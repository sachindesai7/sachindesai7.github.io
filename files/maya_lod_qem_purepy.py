"""
Maya LOD Generator (polyReduce-based, pure cmds)
================================================

Approach:
  1. DUPLICATE the source mesh — this gives us a pristine copy that
     retains ALL attributes from the source: UV sets, vertex normals
     (soft/hard edges), per-face shader assignments, vertex colors.
  2. DETACH from any rig history (skinCluster, blendShapes) so polyReduce
     can modify the duplicate.
  3. Run Maya's native `polyReduce` on the duplicate. Because it's modifying
     an existing mesh (not creating a new one), Maya automatically propagates
     UVs, normals, and shader assignments through the reduction.
  4. Bake the reduce history so the LOD is a clean standalone mesh.
  5. Re-bind to the original skinCluster's influences and copy skin weights
     via closest-point.

This sidesteps the whole hand-rolled mesh-construction problem that the
previous QEM version ran into: when you build a mesh from scratch via the
OpenMaya API, Maya defaults every attribute (normals go to flat face-normals,
no UVs, grey shader). Duplicating inherits all of that for free.

Why polyReduce works here but didn't in our earlier attempts:
  - The earlier failure was specifically on rigged meshes, because the
    source's skinCluster had downstream connections that polyReduce couldn't
    modify. Duplicating breaks those connections; polyReduce then works on
    the duplicate without issue.

INSTALL:
  Drag this file into Maya's viewport — it will copy itself to your Maya
  scripts folder and add a "LOD Gen" shelf button.
"""

import os
import shutil
import sys

import maya.cmds as cmds
import maya.api.OpenMaya as om


# Bump this string any time the script is updated so we can verify the
# installed file is current. It prints on every Generate LODs run.
_SCRIPT_VERSION = "2026-04-22-polyReduce-v8-uv-diagnostics"


# =============================================================================
# Mesh-shape discovery helpers (shared with the old version)
# =============================================================================
def _find_orig_shape(transform_name):
    """If the mesh has a skinCluster/deformer, there's an intermediate 'orig'
    shape with the rest-pose geometry. Return its full path, or None."""
    shapes = cmds.listRelatives(transform_name, shapes=True, type='mesh',
                                fullPath=True) or []
    for s in shapes:
        if cmds.getAttr(s + ".intermediateObject"):
            return s
    return None


def _find_visible_shape(transform_name):
    shapes = cmds.listRelatives(transform_name, shapes=True, type='mesh',
                                fullPath=True, noIntermediate=True) or []
    return shapes[0] if shapes else None


# =============================================================================
# Core: decimate via duplicate + polyReduce
# =============================================================================
def decimate_via_polyreduce(source_transform, keep_percent, new_name,
                            parent_under=None,
                            vertex_weight_map=None,
                            vertex_weight_strength=1.0):
    """Produce a LOD by duplicating the source and running polyReduce on it.

    Args:
        source_transform       : the hi-poly mesh transform
        keep_percent           : 0..100, how much geometry to keep (so 50 = half)
        new_name               : name for the new LOD transform
        parent_under           : if given, reparent the LOD here
        vertex_weight_map      : name of a per-vertex weight map already
                                 painted on the SOURCE (e.g. 'vertexWeights').
                                 White (1.0) = protect, black (0.0) = free to
                                 collapse. None = ignore and reduce uniformly.
                                 See: Mesh > Reduce > [options] paint map.
        vertex_weight_strength : 0..1000 — how aggressively to honour the
                                 weight map. 1.0 is Maya's default; higher
                                 values protect white regions more strongly.

    Returns the LOD transform name, or None on failure.
    """
    # Stash the orig shape's vertex positions BEFORE duplicating. If the rig
    # is currently in a non-bind pose, the duplicate will capture that pose;
    # we fix that by pushing rest positions onto the duplicate from the orig
    # shape afterward.
    orig_shape = _find_orig_shape(source_transform)
    rest_points = None
    if orig_shape:
        try:
            sel = om.MSelectionList()
            sel.add(orig_shape)
            dag = sel.getDagPath(0)
            mfn = om.MFnMesh(dag)
            rest_points = mfn.getPoints(om.MSpace.kObject)
            print("    rest pose : captured {} verts from orig shape"
                  .format(len(rest_points)))
        except Exception as e:
            cmds.warning("Couldn't read orig-shape rest points: {}".format(e))

    # Capture the source's UV set list NOW so we can verify they all survive
    # the duplicate -> polyReduce -> bake-history pipeline. polyReduce is
    # known to drop inactive UV sets when it bakes its history into the mesh.
    source_shape = _find_visible_shape(source_transform)
    source_uv_sets = []
    source_current_uv = None
    if source_shape:
        try:
            source_uv_sets = cmds.polyUVSet(source_shape, query=True,
                                             allUVSets=True) or []
            current = cmds.polyUVSet(source_shape, query=True,
                                     currentUVSet=True) or []
            source_current_uv = current[0] if current else None
            print("    source UV sets: {} (current: {})".format(
                source_uv_sets, source_current_uv))
        except Exception as e:
            cmds.warning("Couldn't query source UV sets: {}".format(e))

    # --- 1. Duplicate source (retains all attributes) ------------------------
    # Duplicate without a name to avoid clashes; we rename at the end.
    dup_nodes = cmds.duplicate(source_transform, renameChildren=True)
    if not dup_nodes:
        cmds.error("Duplicate returned no nodes for '{}'".format(source_transform))
        return None
    dup_name = dup_nodes[0]
    # Get the full DAG path so we can track it through reparenting.
    dup_name = cmds.ls(dup_name, long=True)[0]
    print("    duplicated: {}".format(dup_name))

    # Move to world root so unparenting/deforming doesn't fight the source's
    # constraints. After parenting to world, the name changes because its
    # DAG path is now different. Always re-query after parent operations.
    if cmds.listRelatives(dup_name, parent=True, fullPath=True):
        new_parents = cmds.parent(dup_name, world=True)
        dup_name = cmds.ls(new_parents[0], long=True)[0]
        print("    unparented to world: {}".format(dup_name))

    # --- 2. Strip inherited history (skinCluster, blendShape, etc.) ----------
    # Before deleting history, push rest-pose positions onto the duplicate so
    # the reduction works on bind-pose geometry.
    dup_shape = _find_visible_shape(dup_name)
    if rest_points is not None and dup_shape:
        try:
            sel = om.MSelectionList()
            sel.add(dup_shape)
            dag = sel.getDagPath(0)
            mfn = om.MFnMesh(dag)
            if mfn.numVertices == len(rest_points):
                mfn.setPoints(rest_points, om.MSpace.kObject)
                print("    pushed rest pose onto duplicate")
            else:
                cmds.warning("Vertex count mismatch ({} vs {}); skipping rest-pose push"
                             .format(mfn.numVertices, len(rest_points)))
        except Exception as e:
            cmds.warning("Couldn't push rest points: {}".format(e))

    # Delete construction history on the duplicate — severs the skinCluster
    # and upstream deformer connections so polyReduce has free rein.
    try:
        cmds.delete(dup_name, constructionHistory=True)
    except Exception as e:
        cmds.warning("Couldn't delete history on duplicate: {}".format(e))

    # --- 3. Run polyReduce ---------------------------------------------------
    remove_percent = max(0, min(95, 100 - float(keep_percent)))
    print("    polyReduce: removing {:.1f}% of tris".format(remove_percent))

    # Make sure the FIRST UV set in source_uv_sets is the current one on the
    # duplicate before polyReduce. polyReduce keeps the current set; non-
    # current sets often get dropped during history bake. By making the
    # artist-authored primary set current, we maximize the chance it
    # survives reduction without needing recovery.
    if source_uv_sets and dup_shape:
        try:
            primary_uv = source_uv_sets[0]
            cmds.polyUVSet(dup_shape, currentUVSet=True, uvSet=primary_uv)
            print("    set '{}' as current UV set on duplicate "
                  "(was '{}')".format(primary_uv, source_current_uv))
        except Exception as e:
            cmds.warning("Couldn't set current UV set on duplicate: {}"
                         .format(e))

    # Build the flag dict. We add vertexMapName/vertexWeightCoefficient only
    # if the user wants weight-based protection.
    reduce_args = dict(
        version=1,
        percentage=remove_percent,
        keepQuadsWeight=1.0,
        keepBorder=1,
        keepMapBorder=1,
        keepHardEdge=1,
        keepCreaseEdge=1,
        keepColorBorder=1,
        keepFaceGroupBorder=1,
        # Boost the cost weighting on UV borders, geometry (edge angles),
        # and hard edges so they survive even when vertex weights get mixed
        # in. These default to 1.0; raising them makes polyReduce treat
        # UV shells and shading boundaries as near-inviolable.
        keepBorderWeight=0.5,
        keepMapBorderWeight=0.5,
        keepHardEdgeWeight=0.5,
        keepCreaseEdgeWeight=0.5,
        keepColorBorderWeight=0.5,
        keepFaceGroupBorderWeight=0.5,
        uvWeights=1.0,
        geomWeights=0.5,
        preserveTopology=1,
        replaceOriginal=1,
        ch=True,
    )

    if vertex_weight_map:
        # Confirm the duplicate actually has this weight map before we tell
        # polyReduce to use it — otherwise Maya throws a cryptic error.
        dup_shape_for_check = _find_visible_shape(dup_name)
        has_map = False
        if dup_shape_for_check:
            # Paintable weight maps live as attributes on the shape node.
            if cmds.attributeQuery(vertex_weight_map, node=dup_shape_for_check,
                                   exists=True):
                has_map = True
        if has_map:
            # Clamp strength to a sensible range. Maya's polyReduce
            # weightCoefficient sits on a nonlinear curve — values above
            # ~5 produce harsh artifacts (collapsed triangles get hard
            # edges forced on them, UV borders tear). The slider max of
            # 100 was wishful; we softly cap at 5.
            safe_strength = max(0.1, min(float(vertex_weight_strength), 5.0))

            reduce_args["vertexMapName"] = vertex_weight_map
            reduce_args["vertexWeightCoefficient"] = safe_strength
            reduce_args["weightCoefficient"] = safe_strength
            # `invertVertexWeights=False` => map value 1.0 = protect (default)
            reduce_args["invertVertexWeights"] = False
            print("    vertex weights: using '{}' (strength {:.2f}, "
                  "clamped from {:.1f})".format(
                      vertex_weight_map, safe_strength,
                      vertex_weight_strength))
        else:
            print("    vertex weights: '{}' not found on duplicate, skipping"
                  .format(vertex_weight_map))

    cmds.select(dup_name, replace=True)
    try:
        cmds.polyReduce(dup_name, **reduce_args)
    except Exception as e:
        # Don't swallow — surface the error so we can see it.
        cmds.warning("polyReduce failed on '{}': {}".format(dup_name, e))
        return None

    # Bake the reduce history so the LOD is a clean standalone mesh.
    try:
        cmds.delete(dup_name, constructionHistory=True)
    except Exception:
        pass

    # ---- UV set recovery ----------------------------------------------------
    # polyReduce + history-delete drops inactive UV sets. Compare what we
    # have to what the source had; for any missing set, create it on the LOD
    # and copy values across via transferAttributes targeting that UV set.
    dup_shape_after = _find_visible_shape(dup_name)
    if dup_shape_after and source_uv_sets:
        try:
            current_sets = cmds.polyUVSet(dup_shape_after, query=True,
                                           allUVSets=True) or []
            print("    after reduce, LOD has UV sets: {}".format(current_sets))
            print("    source had UV sets         : {}".format(source_uv_sets))
            missing = [s for s in source_uv_sets if s not in current_sets]
            if not missing:
                print("    UV sets: all preserved, no recovery needed.")
            else:
                print("    *** missing UV sets: {} -- attempting recovery ***"
                      .format(missing))
                for uv_set_name in missing:
                    print("    --> recovering UV set '{}'".format(uv_set_name))

                    # 1. Create the empty UV set on the LOD.
                    try:
                        cmds.polyUVSet(dup_shape_after, create=True,
                                       uvSet=uv_set_name)
                        print("        step 1/3: created empty set on LOD")
                    except Exception as e:
                        cmds.warning("        FAIL step 1: create UV set: {}"
                                     .format(e))
                        continue

                    # 2. Make the set current on BOTH meshes.
                    try:
                        cmds.polyUVSet(source_shape, currentUVSet=True,
                                       uvSet=uv_set_name)
                        cmds.polyUVSet(dup_shape_after, currentUVSet=True,
                                       uvSet=uv_set_name)
                        print("        step 2/3: set as current on both")
                    except Exception as e:
                        cmds.warning("        FAIL step 2: set current: {}"
                                     .format(e))
                        continue

                    # 3. Try transferAttributes for the UV set.
                    transferred = False
                    try:
                        cmds.select(source_transform, replace=True)
                        cmds.select(dup_name, add=True)
                        cmds.transferAttributes(
                            transferUVs=1,         # 1 = current UV set only
                            transferPositions=0,
                            transferNormals=0,
                            transferColors=0,
                            sampleSpace=0,         # world
                            searchMethod=3,        # closest point on surface
                            sourceUvSet=uv_set_name,
                            targetUvSet=uv_set_name,
                        )
                        cmds.delete(dup_name, constructionHistory=True)
                        # Verify the set is non-empty after transfer
                        uv_count = cmds.polyEvaluate(
                            dup_shape_after, uvComponent=True,
                            uvSetName=uv_set_name) or 0
                        if uv_count > 0:
                            print("        step 3/3: transferAttributes OK "
                                  "({} UVs)".format(uv_count))
                            transferred = True
                        else:
                            print("        step 3/3: transferAttributes ran "
                                  "but produced 0 UVs")
                    except Exception as e:
                        cmds.warning("        transferAttributes failed: {}"
                                     .format(e))

                    # 4. Fallback: try polyCopyUV (per-component copy).
                    #    Only useful if topology MATCHES the source — won't
                    #    work after reduction. Kept as a last resort.
                    if not transferred:
                        try:
                            cmds.polyCopyUV(
                                dup_name + ".f[*]",
                                ws=False,
                                uvi=uv_set_name,
                                uvs=uv_set_name,
                                ch=False,
                            )
                            uv_count = cmds.polyEvaluate(
                                dup_shape_after, uvComponent=True,
                                uvSetName=uv_set_name) or 0
                            if uv_count > 0:
                                print("        fallback polyCopyUV OK "
                                      "({} UVs)".format(uv_count))
                                transferred = True
                        except Exception as e:
                            print("        polyCopyUV also failed: {}".format(e))

                    if not transferred:
                        cmds.warning(
                            "        UV set '{}' could NOT be recovered. "
                            "Will need manual Mesh > Transfer Attributes."
                            .format(uv_set_name))

            # 5. Restore the original "current" UV set on both meshes so we
            #    don't leave the source mesh with the wrong active UV set.
            if source_current_uv:
                try:
                    cmds.polyUVSet(source_shape, currentUVSet=True,
                                   uvSet=source_current_uv)
                    if cmds.objExists(dup_shape_after):
                        cmds.polyUVSet(dup_shape_after, currentUVSet=True,
                                       uvSet=source_current_uv)
                except Exception:
                    pass
        except Exception as e:
            cmds.warning("UV-set recovery failed: {}".format(e))

    # --- 4. Rename cleanly and reparent --------------------------------------
    # If a node with the target name already exists, Maya will auto-suffix.
    try:
        lod = cmds.rename(dup_name, new_name)
    except Exception as e:
        cmds.warning("Rename failed: {}".format(e))
        lod = dup_name

    if parent_under and cmds.objExists(parent_under):
        try:
            parented = cmds.parent(lod, parent_under)
            lod = parented[0]
        except Exception as e:
            cmds.warning("Reparent under '{}' failed: {}".format(parent_under, e))

    tri_count = cmds.polyEvaluate(lod, triangle=True) or 0
    vert_count = cmds.polyEvaluate(lod, vertex=True) or 0
    print("    result    : {} verts, {} tris (target {}% kept)".format(
        vert_count, tri_count, int(round(keep_percent))))
    return lod


# =============================================================================
# Skin weight transfer
# =============================================================================
def _find_skin_cluster(transform_name):
    """Return the skinCluster node driving this mesh, or None."""
    shape = _find_visible_shape(transform_name)
    if not shape:
        return None
    history = cmds.listHistory(shape, pruneDagObjects=True,
                                interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'skinCluster':
            return node
    return None


def transfer_skin_weights(source_transform, target_transform):
    """Bind target_transform to the same joints that source_transform is bound
    to (classic linear skinning — legacy bones), then copy per-vertex weights
    via closest-point matching.

    Returns the new skinCluster node name, or None if source isn't skinned.
    """
    source_skin = _find_skin_cluster(source_transform)
    if not source_skin:
        print("  (source has no skinCluster — skipping skin transfer)")
        return None

    influences = cmds.skinCluster(source_skin, query=True, influence=True) or []
    if not influences:
        return None

    print("  skin  : source has {} influences".format(len(influences)))

    # Snap joints to bind pose so the new skinCluster captures the correct
    # rest configuration. dagPose -restore doesn't set keyframes, so any
    # existing animation on the rig is untouched — user can scrub back.
    bind_pose = cmds.listConnections(source_skin + ".bindPose",
                                      destination=False, type='dagPose') or []
    if bind_pose:
        try:
            cmds.dagPose(bind_pose[0], restore=True, g=True)
        except Exception as e:
            cmds.warning("Couldn't restore bind pose: {}".format(e))

    # Bind target with classic linear skinning.
    #   skinMethod = 0 -> classic linear (legacy bones)
    #   bindMethod = 0 -> closest distance
    cmds.select(clear=True)
    cmds.select(influences, replace=True)
    cmds.select(target_transform, add=True)
    target_skin = cmds.skinCluster(
        toSelectedBones=True,
        bindMethod=0,
        skinMethod=0,
        normalizeWeights=1,
        maximumInfluences=4,
        obeyMaxInfluences=True,
        removeUnusedInfluence=False,
        name=target_transform.rsplit("|", 1)[-1] + "_skinCluster",
    )[0]

    # Copy weights by spatial proximity. Uses each skinCluster's bind pose
    # internally, so this is robust as long as the joints are at bind pose
    # (which we just ensured above).
    cmds.copySkinWeights(
        sourceSkin=source_skin,
        destinationSkin=target_skin,
        noMirror=True,
        surfaceAssociation='closestPoint',
        influenceAssociation=['name', 'closestJoint'],
    )
    print("  skin  : bound + copied weights -> {}".format(target_skin))
    return target_skin


# =============================================================================
# Orchestration
# =============================================================================
def _validate_selection():
    sel = cmds.ls(selection=True, long=True, type='transform')
    if not sel:
        cmds.warning("Select one high-poly mesh first.")
        return None
    if len(sel) > 1:
        cmds.warning("Select only ONE mesh (got {}).".format(len(sel)))
        return None
    shapes = cmds.listRelatives(sel[0], shapes=True, type='mesh',
                                fullPath=True, noIntermediate=True)
    if not shapes:
        cmds.warning("'{}' has no polygon mesh shape.".format(sel[0]))
        return None
    return sel[0]





def _detect_reduce_weight_map(source_transform):
    """Look for a paintable polyReduce weight map on the source shape.

    When you use Mesh > Reduce > [paint tool] in Maya, it creates a
    per-vertex float attribute on the shape (commonly named 'vertexWeights'
    or 'weights' depending on Maya version). This attribute name is what we
    pass to polyReduce's vertexMapName flag.

    Returns the attribute name if found, else None.
    """
    shape = _find_visible_shape(source_transform)
    if not shape:
        return None
    # Common names Maya uses for the reduce weight map.
    candidates = ["vertexWeights", "weights", "reduceWeight", "LODWeights"]
    for name in candidates:
        if cmds.attributeQuery(name, node=shape, exists=True):
            # Confirm it has actual painted data (not just the default attr).
            try:
                vals = cmds.getAttr(shape + "." + name) or []
                # Paint tool stores per-vertex scalars. Accept it if any
                # value differs from the default 1.0 — otherwise it was
                # never touched and won't affect the reduction.
                if isinstance(vals, list) and vals:
                    flat = vals[0] if isinstance(vals[0], (list, tuple)) else vals
                    if any(abs(v - 1.0) > 1e-4 for v in flat):
                        return name
                # Even if untouched, return the name so user's override works.
                return name
            except Exception:
                return name
    return None


# =============================================================================
# Orchestration
# =============================================================================
def generate_lods(lod1_remove=50, lod2_remove=50,
                  transfer_skin=True,
                  use_vertex_weights=True,
                  vertex_weight_strength=2.0,
                  # Kept for backward compatibility with old UI state —
                  # polyReduce handles these automatically now.
                  transfer_uvs=True,
                  transfer_normals=True,
                  transfer_shaders=True):
    """Generate two LODs from the selected mesh. See module docstring.

    Args:
        lod1_remove / lod2_remove : percent of triangles to remove at each LOD
        transfer_skin             : rebind LODs to the source's joints and
                                    copy skin weights by closest-point
        use_vertex_weights        : if True, look for a paintable weight map
                                    on the source (Mesh > Reduce > [paint
                                    tool]) and feed it into polyReduce. White
                                    painted vertices are protected; black
                                    ones are free to collapse.
        vertex_weight_strength    : 1..100, how strongly to honour the weight
                                    map. 10 is a reasonable default for
                                    visible protection; set higher to
                                    protect white regions more aggressively.
    """
    print("")
    print("=" * 60)
    print(" LOD Generator  [version: {}]".format(_SCRIPT_VERSION))
    print("=" * 60)

    source = _validate_selection()
    if not source:
        print(" No valid selection; aborting.")
        return

    print(" Source      : {}".format(source))

    # Confirm source has a polygon shape we can actually reduce.
    shape = _find_visible_shape(source)
    if not shape:
        print(" No polygon shape found on '{}'; aborting.".format(source))
        return
    print(" Shape       : {}".format(shape))
    print(" Source stats: {} verts, {} tris".format(
        cmds.polyEvaluate(source, vertex=True),
        cmds.polyEvaluate(source, triangle=True)))

    short = source.rsplit("|", 1)[-1]
    # Compound percentages:
    #   LOD1 keep = (100 - r1)/100
    #   LOD2 keep = LOD1_keep * (100 - r2)/100
    # 50/50 -> LOD1 at 50% of original, LOD2 at 25% of original.
    keep1_pct = (100.0 - float(lod1_remove))
    keep2_pct = keep1_pct * (100.0 - float(lod2_remove)) / 100.0

    parent = cmds.listRelatives(source, parent=True, fullPath=True)
    parent_under = parent[0] if parent else None
    print(" Parent under: {}".format(parent_under or "<world>"))

    # Look for a paintable reduce weight map on the source.
    weight_map = None
    if use_vertex_weights:
        weight_map = _detect_reduce_weight_map(source)
        if weight_map:
            print(" Weight map  : '{}' detected (strength {:.1f})".format(
                weight_map, vertex_weight_strength))
        else:
            print(" Weight map  : none found (uniform reduction)")

    cmds.waitCursor(state=True)
    try:
        print("")
        print(" --- LOD1 (keep {:.0f}%) ---".format(keep1_pct))
        try:
            lod1 = decimate_via_polyreduce(
                source, keep1_pct, "{}_LOD1".format(short),
                parent_under=parent_under,
                vertex_weight_map=weight_map,
                vertex_weight_strength=vertex_weight_strength)
        except Exception as e:
            import traceback
            print("\n*** LOD1 FAILED ***")
            traceback.print_exc()
            return
        if not lod1:
            print(" LOD1 returned None; aborting.")
            return
        print(" LOD1 created: {}".format(lod1))
        if transfer_skin:
            try:
                transfer_skin_weights(source, lod1)
            except Exception as e:
                import traceback
                print("\n*** Skin transfer on LOD1 FAILED ***")
                traceback.print_exc()

        print("")
        print(" --- LOD2 (keep {:.1f}%) ---".format(keep2_pct))
        try:
            lod2 = decimate_via_polyreduce(
                source, keep2_pct, "{}_LOD2".format(short),
                parent_under=parent_under,
                vertex_weight_map=weight_map,
                vertex_weight_strength=vertex_weight_strength)
        except Exception as e:
            import traceback
            print("\n*** LOD2 FAILED ***")
            traceback.print_exc()
            return
        if not lod2:
            print(" LOD2 returned None.")
            return
        print(" LOD2 created: {}".format(lod2))
        if transfer_skin:
            try:
                transfer_skin_weights(source, lod2)
            except Exception:
                import traceback
                print("\n*** Skin transfer on LOD2 FAILED ***")
                traceback.print_exc()

        cmds.select(source, replace=True)
        print("")
        print("=" * 60)
        print(" Done.")
        print("=" * 60)
    finally:
        cmds.waitCursor(state=False)


def show_ui():
    WIN_NAME = "qemLodGenWin"
    if cmds.window(WIN_NAME, exists=True):
        cmds.deleteUI(WIN_NAME)

    window = cmds.window(WIN_NAME, title="LOD Generator (QEM, pure Python)",
                         widthHeight=(400, 470), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8,
                      columnAttach=('both', 14))

    cmds.text(label="LOD Generator — Quadric Error Metrics",
              font='boldLabelFont', align='center', height=24)
    cmds.text(label="Pure Python — no NumPy / no external SDK.",
              align='center', font='smallPlainLabelFont')
    cmds.separator(height=6, style='in')

    s1 = cmds.intSliderGrp('qemPPLodSlider1', field=True,
                           label='LOD1  remove %',
                           minValue=1, maxValue=95, value=50,
                           columnWidth3=(100, 45, 160))
    s2 = cmds.intSliderGrp('qemPPLodSlider2', field=True,
                           label='LOD2  remove %',
                           minValue=1, maxValue=95, value=50,
                           columnWidth3=(100, 45, 160))

    cmds.text(
        label=("LOD1 from ORIGINAL, LOD2 from LOD1.\n"
               "50 / 50  ->  LOD1 ~50% of original, LOD2 ~25%.\n"
               "Expect ~30-60s for a 5k-tri mesh."),
        align='left', font='smallPlainLabelFont')

    cmds.separator(height=4, style='none')
    cmds.text(label="Transfer from source:", align='left',
              font='smallBoldLabelFont')
    uvs_cb   = cmds.checkBox('qemPPLodUVsCB',
                             label='UVs',                       value=True)
    norm_cb  = cmds.checkBox('qemPPLodNormCB',
                             label='Normals (soft/hard edges)', value=True)
    shade_cb = cmds.checkBox('qemPPLodShadeCB',
                             label='Shader / material assignments',
                             value=True)
    skin_cb  = cmds.checkBox('qemPPLodSkinCB',
                             label='Skin weights (legacy linear)',
                             value=True)

    cmds.separator(height=4, style='none')
    cmds.text(label="Vertex weight painting (protect important areas):",
              align='left', font='smallBoldLabelFont')
    vw_cb = cmds.checkBox('qemPPLodVWCB',
                          label=("Use painted reduce weights from source "
                                 "(white=protect, black=collapse)"),
                          value=True)
    vw_strength = cmds.floatSliderGrp('qemPPLodVWStrength', field=True,
                                      label='Protection strength:',
                                      minValue=0.5, maxValue=5.0,
                                      value=2.0, precision=1,
                                      columnWidth3=(130, 55, 150))

    cmds.separator(height=6, style='in')

    def _on_generate(*_):
        r1 = cmds.intSliderGrp(s1, query=True, value=True)
        r2 = cmds.intSliderGrp(s2, query=True, value=True)
        generate_lods(
            r1, r2,
            transfer_skin          = cmds.checkBox(skin_cb,  query=True, value=True),
            use_vertex_weights     = cmds.checkBox(vw_cb,    query=True, value=True),
            vertex_weight_strength = cmds.floatSliderGrp(vw_strength, query=True, value=True),
            transfer_uvs           = cmds.checkBox(uvs_cb,   query=True, value=True),
            transfer_normals       = cmds.checkBox(norm_cb,  query=True, value=True),
            transfer_shaders       = cmds.checkBox(shade_cb, query=True, value=True),
        )

    cmds.button(label="Generate LODs", height=38,
                backgroundColor=(0.30, 0.55, 0.30), command=_on_generate)
    cmds.button(label="Close", height=24,
                command=lambda *_: cmds.deleteUI(window))

    cmds.showWindow(window)


if __name__ == "__main__":
    # Allow developers to run the module directly from inside Maya's Script
    # Editor as well — e.g. after reloading during development.
    show_ui()


# =============================================================================
# Drag-and-drop installer
# =============================================================================
# Maya calls onMayaDroppedPythonFile(obj) automatically after executing any
# Python file that gets dragged onto the viewport. We use that hook to copy
# this script to the user's Maya scripts folder and install a shelf button.

_INSTALLED_MODULE_NAME = "maya_lod_qem_purepy"
_SHELF_BUTTON_LABEL    = "LOD Gen"
_SHELF_BUTTON_COMMAND  = (
    "# Auto-generated by LOD Generator installer\n"
    "import importlib\n"
    "try:\n"
    "    import {mod} as _lodgen\n"
    "    importlib.reload(_lodgen)\n"
    "except ImportError as e:\n"
    "    import maya.cmds as _cmds\n"
    "    _cmds.warning('LOD Generator not found on scripts path: ' + str(e))\n"
    "else:\n"
    "    _lodgen.show_ui()\n"
).format(mod=_INSTALLED_MODULE_NAME)


def _install_to_scripts_dir(source_path):
    """Copy this script into Maya's user scripts folder under the canonical
    module name, so the shelf button can import it."""
    import os
    import shutil
    import sys

    scripts_dir = cmds.internalVar(userScriptDir=True)
    dest_path = os.path.join(scripts_dir, _INSTALLED_MODULE_NAME + ".py")

    try:
        src_abs  = os.path.normcase(os.path.abspath(source_path))
        dest_abs = os.path.normcase(os.path.abspath(dest_path))
    except Exception:
        src_abs = dest_abs = ""

    if src_abs and src_abs != dest_abs:
        shutil.copy2(source_path, dest_path)
        print("[LOD Gen] copied script -> {}".format(dest_path))
    else:
        print("[LOD Gen] script already at {}".format(dest_path))

    # Make sure the scripts dir is importable right now so the shelf button
    # works without a Maya restart.
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # Drop any cached copy of an older version so `import` below re-reads
    # the freshly-copied file.
    sys.modules.pop(_INSTALLED_MODULE_NAME, None)

    return dest_path


def _install_shelf_button():
    """Add (or replace) the shelf button on the currently active shelf."""
    import maya.mel as mel

    # The active shelf is the selected tab of the global shelf tabLayout.
    shelf_top = mel.eval("global string $gShelfTopLevel; $tmp=$gShelfTopLevel;")
    if not shelf_top or not cmds.tabLayout(shelf_top, exists=True):
        cmds.warning("[LOD Gen] Shelf UI not available; button not added.")
        return None

    current_shelf = cmds.tabLayout(shelf_top, query=True, selectTab=True)
    if not current_shelf:
        cmds.warning("[LOD Gen] No active shelf to add the button to.")
        return None

    # Remove any existing button from a previous install so we don't stack up.
    existing = cmds.shelfLayout(current_shelf, query=True, childArray=True) or []
    for btn in existing:
        try:
            if not cmds.shelfButton(btn, exists=True):
                continue
            if cmds.shelfButton(btn, query=True, label=True) == _SHELF_BUTTON_LABEL:
                cmds.deleteUI(btn)
        except Exception:
            pass

    # Create the new button. image="polyReduce.png" is a Maya built-in;
    # imageOverlayLabel falls back gracefully if the icon is missing.
    cmds.shelfButton(
        parent=current_shelf,
        label=_SHELF_BUTTON_LABEL,
        annotation="LOD Generator — QEM mesh reduction with skin weight transfer",
        image="polyReduce.png",
        imageOverlayLabel="LOD",
        overlayLabelColor=(0.95, 0.95, 0.95),
        overlayLabelBackColor=(0, 0, 0, 0.5),
        sourceType="python",
        command=_SHELF_BUTTON_COMMAND,
    )

    # Persist the shelf so the button survives a Maya restart.
    try:
        mel.eval('saveAllShelves $gShelfTopLevel;')
    except Exception:
        pass

    return current_shelf


def onMayaDroppedPythonFile(obj=None):
    """Entry point Maya calls when this .py file is dragged onto the viewport."""
    # __file__ is set by Python when Maya execfile()s the dropped file.
    try:
        source_path = __file__
    except NameError:
        cmds.warning("[LOD Gen] Couldn't locate dropped script path. "
                     "Copy this file into your Maya scripts folder manually.")
        return

    try:
        _install_to_scripts_dir(source_path)
    except Exception as e:
        cmds.error("[LOD Gen] Copy failed: {}".format(e))
        return

    shelf = _install_shelf_button()

    msg = ("<hl>LOD Generator installed.</hl> "
           "Click the '{}' button on your shelf to launch.".format(
               _SHELF_BUTTON_LABEL))
    try:
        cmds.inViewMessage(amg=msg, pos='midCenter', fade=True,
                           fadeStayTime=3500, dragKill=True)
    except Exception:
        pass
    print("[LOD Gen] install complete"
          + (" (shelf: {})".format(shelf) if shelf else ""))


