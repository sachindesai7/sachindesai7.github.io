# ================================================================
# BATCH FBX EXPORTER PRO — Project B.L.A.C.K. | Lila Games
# Animation & Rig Export Tool for Maya to Unity
# Version 2.0 — Based on working pipeline
# ================================================================
#
# INSTALL:
#   Just drag this file into Maya's viewport. It will:
#     1. Copy itself to your Maya scripts folder.
#     2. Add an "FBX PRO" button to the currently active shelf.
#     3. Save the shelf so the button survives a Maya restart.
#   Click the shelf button any time after that to launch the tool.
#   To reinstall/update, drag the file in again — the old button is replaced.
#
# ================================================================

import maya.cmds as cmds
import maya.mel as mel
import os
import time
import json

# ================================================================
# 1. CONSTANTS
# ================================================================
WINDOW_NAME   = "batchFBXExporterWin"
WINDOW_TITLE  = "Batch FBX Exporter PRO v2.0 — Lila Games"
ROOT_JOINT    = "TrajectorySHJnt"
MESH_GRP      = "Mesh_grp"

SETTINGS_FILE = os.path.join(
                    os.path.expanduser("~"),
                    "Documents", "maya",
                    "batch_fbx_settings.json")

# Global — stores per-file checkbox references
file_options = {}


# ================================================================
# 2. SETTINGS — save/load last used paths
# ================================================================

def load_settings():
    """Load last used paths from JSON file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Could not load settings: {e}")
    return {"source_folder": "", "export_folder": ""}


def save_settings(src, dst):
    """Save current paths to JSON file"""
    try:
        folder = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(folder):
            os.makedirs(folder)
        settings = {
            "source_folder" : src,
            "export_folder" : dst,
            "last_used"     : time.strftime("%Y-%m-%d %H:%M")
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Could not save settings: {e}")


# ================================================================
# 3. CORE PIPELINE — exactly from working version
# ================================================================

def prevent_save():
    cmds.file(modified=False)


def initialize_fbx():
    if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
        cmds.loadPlugin("fbxmaya")
    try:
        if not cmds.pluginInfo("mtoa", q=True, loaded=True):
            cmds.loadPlugin("mtoa")
    except Exception:
        print("    Arnold not available, skipping")
    mel.eval("FBXResetExport;")


def validate_scene():
    cmds.currentUnit(time="ntsc")
    cmds.currentUnit(linear="cm")
    mel.eval('setUpAxis "y";')


def get_range():
    return (int(cmds.playbackOptions(q=True, min=True)),
            int(cmds.playbackOptions(q=True, max=True)))


def import_refs():
    refs = cmds.ls(type="reference") or []
    for r in refs:
        if "sharedReferenceNode" in r:
            continue
        try:
            f = cmds.referenceQuery(r, filename=True)
            cmds.file(f, importReference=True)
        except Exception:
            pass


def delete_namespaces():
    nss = cmds.namespaceInfo(
              listOnlyNamespaces=True,
              recurse=True) or []
    for ns in sorted(nss, reverse=True):
        if ns not in ["UI", "shared"]:
            try:
                cmds.namespace(
                    removeNamespace=ns,
                    mergeNamespaceWithParent=True)
            except Exception:
                pass


def remove_arnold_nodes():
    try:
        arnold_nodes = cmds.ls(
            type=["aiOptions",
                  "aiAOVDriver",
                  "aiAOVFilter"]) or []
        if arnold_nodes:
            cmds.delete(arnold_nodes)
    except Exception:
        pass


def collapse_to_base_layer(start, end):
    cmds.select(ROOT_JOINT, hierarchy=True)
    joints = cmds.ls(sl=True)
    cmds.bakeResults(joints,
                     time=(start, end),
                     simulation=True,
                     sampleBy=1)
    layers = cmds.ls(type="animLayer") or []
    for l in layers:
        if l != "BaseAnimation":
            try:
                cmds.delete(l)
            except Exception:
                pass


def clean_locators():
    if not cmds.objExists(ROOT_JOINT):
        return

    all_nodes = cmds.listRelatives(
                    ROOT_JOINT,
                    ad=True,
                    fullPath=True) or []
    locator_transforms = []

    for node in all_nodes:
        if not cmds.objExists(node):
            continue
        try:
            shapes = cmds.listRelatives(
                         node,
                         shapes=True,
                         fullPath=True) or []
        except Exception:
            continue
        for s in shapes:
            if not cmds.objExists(s):
                continue
            try:
                if cmds.nodeType(s) == "locator":
                    locator_transforms.append(node)
                    break
            except Exception:
                pass

    keep = set()
    for loc in locator_transforms:
        short_name = loc.split("|")[-1]
        if "r_Arm_Elbow_CurveSHJnt" in loc:
            continue
        if short_name == "WeaponLocator":
            keep.add(loc)
            try:
                children = cmds.listRelatives(
                               loc,
                               ad=True,
                               fullPath=True) or []
                keep.update(children)
            except Exception:
                pass

    to_delete = []
    for loc in locator_transforms:
        if not cmds.objExists(loc):
            continue
        if "r_Arm_Elbow_CurveSHJnt" in loc:
            to_delete.append(loc)
            continue
        if loc not in keep:
            to_delete.append(loc)

    if to_delete:
        try:
            cmds.delete(to_delete)
            print(f"    Deleted {len(to_delete)} locators")
        except Exception as e:
            print(f"    Locator delete failed: {e}")


def delete_constraints_on_skeleton():
    cmds.select(ROOT_JOINT, hierarchy=True)
    joints = cmds.ls(sl=True)
    constraints = cmds.listRelatives(
                      joints,
                      type="constraint",
                      allDescendents=True) or []
    if constraints:
        cmds.delete(constraints)


def cleanup():
    cmds.select(ROOT_JOINT, hierarchy=True)
    mel.eval("delete -constraints;")
    if cmds.listRelatives(ROOT_JOINT, parent=True):
        cmds.parent(ROOT_JOINT, world=True)


def get_mesh_transforms():
    meshes = cmds.listRelatives(
                 MESH_GRP,
                 ad=True,
                 type="mesh") or []
    return list(set(
        cmds.listRelatives(meshes, parent=True) or []))


def unparent_to_world(nodes):
    result = []
    for n in nodes:
        try:
            if cmds.listRelatives(n, parent=True):
                cmds.parent(n, world=True)
            result.append(n)
        except Exception:
            pass
    return result


def export_anim(export_folder, file_path):
    name = os.path.splitext(
               os.path.basename(file_path))[0]
    path = os.path.join(
               export_folder,
               name + ".fbx").replace("\\", "/")

    cmds.select(ROOT_JOINT, hierarchy=True)

    mel.eval("FBXResetExport;")
    mel.eval('FBXExportConvertUnitString -v "cm";')
    mel.eval(f'FBXExport -f "{path}" -s;')

    print(f"    Animation Exported: {path}")
    return path


def export_rig(export_folder, file_path):
    name = os.path.splitext(
               os.path.basename(file_path))[0]
    path = os.path.join(
               export_folder,
               name + "_rig.fbx").replace("\\", "/")

    if not cmds.objExists(MESH_GRP) or \
       not cmds.objExists(ROOT_JOINT):
        print("    Missing Mesh_grp or root joint")
        return None

    mesh_transforms = get_mesh_transforms()
    if not mesh_transforms:
        print("    No mesh found")
        return None

    delete_constraints_on_skeleton()
    mesh_transforms = unparent_to_world(mesh_transforms)
    unparent_to_world([ROOT_JOINT])

    cmds.select(clear=True)
    cmds.select(mesh_transforms, add=True)
    cmds.select(ROOT_JOINT, hierarchy=True, add=True)
    cmds.currentTime(0)

    mel.eval("FBXResetExport;")
    mel.eval('FBXExportConvertUnitString -v "cm";')
    mel.eval(f'FBXExport -f "{path}" -s;')

    print(f"    Rig Exported: {path}")
    return path


# ================================================================
# 4. PROCESS SINGLE FILE
# ================================================================

def process_file(file_path, export_folder,
                 do_anim, do_rig):
    """Process one file — same logic as working version"""
    file_name = os.path.basename(file_path)
    result = {
        "file"     : file_name,
        "status"   : "failed",
        "exported" : [],
        "error"    : ""
    }

    try:
        print(f"\n  Processing: {file_name}")

        cmds.file(file_path, open=True, force=True)
        prevent_save()

        validate_scene()
        initialize_fbx()

        start, end = get_range()

        import_refs()
        delete_namespaces()
        remove_arnold_nodes()

        if do_anim:
            collapse_to_base_layer(start, end)
            clean_locators()
            cleanup()
            path = export_anim(export_folder, file_path)
            if path:
                result["exported"].append(path)

        if do_rig:
            path = export_rig(export_folder, file_path)
            if path:
                result["exported"].append(path)

        prevent_save()
        result["status"] = "success"
        print(f"  SUCCESS: {file_name}")

    except Exception as e:
        result["status"] = "failed"
        result["error"]  = str(e)
        print(f"  FAILED: {file_name} — {e}")

    return result


# ================================================================
# 5. REPORT WRITER
# ================================================================

def write_report(export_folder, results, total_time):
    """Write export report txt to export folder"""
    try:
        report_path = os.path.join(
                          export_folder,
                          "FBX_Export_Report.txt")
        timestamp   = time.strftime("%Y-%m-%d %H:%M:%S")

        success_list = [r for r in results
                        if r["status"] == "success"]
        failed_list  = [r for r in results
                        if r["status"] == "failed"]

        with open(report_path, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("  FBX EXPORT REPORT — Lila Games\n")
            f.write("  Project B.L.A.C.K.\n")
            f.write("=" * 60 + "\n")
            f.write(f"  Date     : {timestamp}\n")
            f.write(f"  Exported : {len(success_list)}\n")
            f.write(f"  Failed   : {len(failed_list)}\n")
            f.write(f"  Total    : {len(results)}\n")
            f.write(f"  Time     : {total_time:.1f}s\n")
            f.write("=" * 60 + "\n\n")

            f.write("SUCCESSFULLY EXPORTED:\n")
            f.write("-" * 60 + "\n")
            if success_list:
                for i, r in enumerate(success_list, 1):
                    f.write(f"  {i}. {r['file']}\n")
                    for p in r["exported"]:
                        f.write(f"     -> {p}\n")
            else:
                f.write("  None\n")

            f.write("\nFAILED EXPORTS:\n")
            f.write("-" * 60 + "\n")
            if failed_list:
                for i, r in enumerate(failed_list, 1):
                    f.write(f"  {i}. {r['file']}\n")
                    f.write(f"     Error: {r['error']}\n")
            else:
                f.write("  None — all exported!\n")

            f.write("\n" + "=" * 60 + "\n")

        print(f"\n  Report saved: {report_path}")

    except Exception as e:
        print(f"  Report write failed: {e}")


# ================================================================
# 6. UI FUNCTIONS
# ================================================================

def browse_folder(field_name):
    """Open folder browser and set path in field"""
    folder = cmds.fileDialog2(
                 fileMode=3,
                 caption="Select Folder",
                 okCaption="Select")
    if folder:
        cmds.textField(field_name,
                       edit=True,
                       text=folder[0])
        try:
            src = cmds.textField("src",
                                 q=True, text=True)
            dst = cmds.textField("dst",
                                 q=True, text=True)
            save_settings(src, dst)
        except Exception:
            pass


def load_files():
    """Scan source folder and build file list"""
    src = cmds.textField("src", q=True, text=True)

    if not os.path.exists(src):
        cmds.warning("Invalid source folder")
        return

    files = [f for f in os.listdir(src)
             if f.endswith((".ma", ".mb"))]

    if not files:
        cmds.warning("No Maya files found!")
        return

    # Clear existing list
    children = cmds.columnLayout(
                   "fileList",
                   q=True,
                   childArray=True) or []
    for c in children:
        try:
            cmds.deleteUI(c)
        except Exception:
            pass

    file_options.clear()

    # Build file rows
    for f in files:
        cmds.rowLayout(
            parent="fileList",
            nc=3,
            adjustableColumn=1)
        cmds.text(label=f, width=250)
        anim_cb = cmds.checkBox(label="Anim",
                                value=True)
        rig_cb  = cmds.checkBox(label="Rig",
                                value=False)
        file_options[f] = {
            "anim" : anim_cb,
            "rig"  : rig_cb
        }
        cmds.setParent("..")

    print(f"Loaded {len(files)} files")


def select_all_anim(value):
    for f in file_options:
        cmds.checkBox(file_options[f]["anim"],
                      e=True, value=value)


def select_all_rig(value):
    for f in file_options:
        cmds.checkBox(file_options[f]["rig"],
                      e=True, value=value)


def run_batch_ui(*args):
    """Main export handler"""
    src = cmds.textField("src", q=True, text=True)
    dst = cmds.textField("dst", q=True, text=True)

    if not src or not os.path.exists(src):
        cmds.warning("Invalid source folder!")
        return

    if not dst:
        cmds.warning("Please set export folder!")
        return

    if not os.path.exists(dst):
        os.makedirs(dst)

    if not file_options:
        cmds.warning("Please load files first!")
        return

    save_settings(src, dst)

    start_time = time.time()
    results    = []

    print("\n" + "=" * 60)
    print("  BATCH EXPORT STARTED — Lila Games")
    print("=" * 60)

    for f in file_options:
        do_anim = cmds.checkBox(
                      file_options[f]["anim"],
                      q=True, value=True)
        do_rig  = cmds.checkBox(
                      file_options[f]["rig"],
                      q=True, value=True)

        if not (do_anim or do_rig):
            continue

        file_path = os.path.join(src, f)

        # Skip failures — continue to next file!
        try:
            result = process_file(file_path, dst,
                                  do_anim, do_rig)
            results.append(result)
        except Exception as e:
            results.append({
                "file"     : f,
                "status"   : "failed",
                "exported" : [],
                "error"    : str(e)
            })
            print(f"  Skipping {f}: {e}")
            continue

    total_time   = time.time() - start_time
    success_list = [r for r in results
                    if r["status"] == "success"]
    failed_list  = [r for r in results
                    if r["status"] == "failed"]

    write_report(dst, results, total_time)

    print("\n" + "=" * 60)
    print(f"  COMPLETE!")
    print(f"  Exported : {len(success_list)}")
    print(f"  Failed   : {len(failed_list)}")
    print(f"  Time     : {total_time:.1f}s")
    print("=" * 60)

    cmds.confirmDialog(
        title="Export Complete",
        message=(f"Batch export finished!\n\n"
                 f"Exported : {len(success_list)}\n"
                 f"Failed   : {len(failed_list)}\n"
                 f"Time     : {total_time:.0f}s\n\n"
                 f"Report saved to export folder."),
        button=["OK"])


# ================================================================
# 7. BUILD UI
# ================================================================

def build_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(WINDOW_NAME,
                title=WINDOW_TITLE,
                widthHeight=(600, 550))

    cmds.columnLayout(adjustableColumn=True)

    # Title
    cmds.text(label="BATCH FBX EXPORTER PRO",
              height=30,
              font="boldLabelFont",
              align="center")

    cmds.separator(height=8)

    # Source folder
    cmds.text(label="Source Folder (Maya files):",
              align="left")
    cmds.rowLayout(nc=2, adjustableColumn=1)
    cmds.textField("src",
                   placeholderText="Maya files folder...")
    cmds.button(label="Browse",
                width=80,
                command=lambda x: browse_folder("src"))
    cmds.setParent("..")

    cmds.button(label="Load Files",
                command=lambda x: load_files())

    cmds.separator(height=8)

    # Export folder
    cmds.text(label="Export Folder (FBX output):",
              align="left")
    cmds.rowLayout(nc=2, adjustableColumn=1)
    cmds.textField("dst",
                   placeholderText="FBX export folder...")
    cmds.button(label="Browse",
                width=80,
                command=lambda x: browse_folder("dst"))
    cmds.setParent("..")

    cmds.separator(height=8)

    # Select all controls
    cmds.rowLayout(nc=4)
    cmds.button(label="All Anim ON",  width=130,
                command=lambda x: select_all_anim(True))
    cmds.button(label="All Anim OFF", width=130,
                command=lambda x: select_all_anim(False))
    cmds.button(label="All Rig ON",   width=130,
                command=lambda x: select_all_rig(True))
    cmds.button(label="All Rig OFF",  width=130,
                command=lambda x: select_all_rig(False))
    cmds.setParent("..")

    # File list
    cmds.scrollLayout(height=220,
                      childResizable=True)
    cmds.columnLayout("fileList",
                      adjustableColumn=True)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(height=8)

    # Export button
    cmds.button(label="EXPORT SELECTED",
                height=50,
                backgroundColor=(0.15, 0.55, 0.15),
                command=run_batch_ui)

    # Close button
    cmds.button(label="Close",
                height=28,
                command=lambda x: cmds.deleteUI(
                    WINDOW_NAME))

    cmds.text(label="Maya files will NOT be saved",
              align="center")

    cmds.showWindow(WINDOW_NAME)

    # Load saved settings
    settings = load_settings()
    if settings.get("source_folder"):
        cmds.textField("src", edit=True,
                       text=settings["source_folder"])
    if settings.get("export_folder"):
        cmds.textField("dst", edit=True,
                       text=settings["export_folder"])

    print("Batch FBX Exporter PRO opened!")


# ================================================================
# 8. SHELF INSTALLER
# ================================================================

def install_shelf_button():
    """Run once to add tool to Maya shelf"""
    try:
        current_shelf = mel.eval(
            "global string $gShelfTopLevel; "
            "tabLayout -q -selectTab "
            "$gShelfTopLevel;")

        script_path = os.path.abspath(__file__)
        script_dir  = os.path.dirname(
                          script_path).replace("\\", "/")

        shelf_command = (
            f'import sys\n'
            f'import importlib\n'
            f'if r"{script_dir}" not in sys.path:\n'
            f'    sys.path.append(r"{script_dir}")\n'
            f'import batch_fbx_exporter_pro as exp\n'
            f'importlib.reload(exp)\n'
            f'exp.main()'
        )

        cmds.shelfButton(
            parent=current_shelf,
            label="FBX PRO",
            annotation="Batch FBX Exporter PRO",
            image="pythonFamily.png",
            sourceType="python",
            command=shelf_command,
            imageOverlayLabel="FBX")

        print(f"Shelf button installed!")

    except Exception as e:
        print(f"Shelf install failed: {e}")


# ================================================================
# 9. MAIN
# ================================================================

def main():
    build_ui()


# ================================================================
# 10. DRAG-AND-DROP INSTALLER
# ================================================================
# Maya automatically calls onMayaDroppedPythonFile(obj) after executing any
# .py file dropped onto the viewport. We use that to copy this script to the
# user's Maya scripts folder and create a shelf button that imports from the
# installed location — independent of wherever the file was dragged from.

_INSTALLED_MODULE_NAME = "batch_fbx_exporter_pro"
_SHELF_BUTTON_LABEL    = "FBX PRO"
_ICON_FILE_NAME        = "fbx_pro_icon.png"
_SHELF_BUTTON_COMMAND  = (
    "# Auto-generated by Batch FBX Exporter PRO installer\n"
    "import importlib\n"
    "try:\n"
    "    import {mod} as _fbxpro\n"
    "    importlib.reload(_fbxpro)\n"
    "except ImportError as e:\n"
    "    import maya.cmds as _cmds\n"
    "    _cmds.warning('Batch FBX Exporter PRO not on scripts path: ' + str(e))\n"
    "else:\n"
    "    _fbxpro.main()\n"
).format(mod=_INSTALLED_MODULE_NAME)

# Custom 32x32 shelf icon, base64-encoded PNG. Sized to exactly match
# Maya's shelf slot (32x32) with solid fill so no scaling or alpha
# interpretation is involved - this avoids the squished / clipped
# rendering that happens when Maya tries to resize larger icons with
# transparent corners.
_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAADnElEQVR42u2UbUxbVRjH/7e3lJW2"
    "UNsCl7VjkA1qF0dRZpmEgpt7cXdM0SCytWp8SQzGYLQJ8mUZCcnMopihcbjFfdFBpixzW5n7sCwZ"
    "6jBAwAwSS9kQIm5rRSQbL6XlnnP9gFduB4uLfKiJPcn5cE5+5zm/c54nD/Ny8dciYjiUhAqIqQCl"
    "JC7wPxcg8RSICwKH2yqRZTUuAYYGgqh1nV6WmY8QBG9M4bLXj1Of9QEA8ovW4EBzGQCg4Y3z6Lvy"
    "CwDgkeJM7P9k95J9BaUCKBUgYqEftbS0+BiGaZSmNY9r/Pb6odblGEfhpi/SLRrqrilErjM0TKmA"
    "vu9HcPL4pTsMA7xev2k2nDA6ptMnoKZhCxgGaGo63Hvg0z2NgTsDo5QK8hQsNkRzSoEtf7Wbl//E"
    "AhfNmMNufiI4TTjLA7BYlbcvnun2mVMKbF9+/FOyvXDt9IaN67U1DVvHjZp1RG9MYvv7Bybq6uq+"
    "yzaUFJiScrMoJVAQSkAogShryKIoQtqXz7uZzBwDTFwKCwBdXV2BydBogFCCcDiCD2s71KHZkLCL"
    "37nWUbqeDc3Okaqq58+pYDTkmHY5pZgKSknU61wul+3G7V7+wqAHFwY9eK22BPdijpx9EUqlAt3d"
    "PQGv1zucnLiGk9ix4Qn2yiU/lYTPnjtzbWjw+lQet7cMIsNK3KLAX6+7uwYqXnU0+se9Hcsxqamp"
    "Rzo7O286HI9yX508/axJnbtOipdXaMETu+0qSaCystJazr/kUCuNBomhlCzWgCjLL6e12zakViyp"
    "gSWMroL3/TA7X1QEOEsfS3sh+GZ7Xrr7GZ1ejXff3wNGwaC5ufkqAFRXV9ubjtY/5N5+6FfFXJpF"
    "iiNLQXR+5Zb3YnT6RGx+3JoAAD09PYHJ0MgYpQSegzxMnA6DPv+kx+O5/EF964Tf9/OM2WzWvv3e"
    "DiEsTIUWUyASUDH6dSJESPvyKcpqIDB9lW/regemDJ3YeqJtxOVyfaNLzOD4qnw4n7QhEpmn+1x7"
    "2xlBk7w60Vly8K32VXNzYfLU02VZm8vVQ1JMpiRz/9839waOfT4TCY6naTbaHjSW88t1LomR1gzD"
    "siqFJkm/KjszW7+lWMXqtLem+/qv/XH+IsOw7MPpr+zTqrg0AJiZ/+33HwPHW6goCDkGfluGtsAe"
    "JRCLoUCMR1wgLhBzAeX9QB01bf/6gtKPnlvZD6zk8vs5/9+vgX/6wpWej7fimAv8CdVDE99hgmiO"
    "AAAAAElFTkSuQmCC"
)


def _dragdrop_copy_to_scripts(source_path):
    """Copy this script into Maya's user scripts folder under the canonical
    module name, so the shelf button can always find it."""
    import shutil
    import sys

    scripts_dir = cmds.internalVar(userScriptDir=True)
    dest_path = os.path.join(scripts_dir,
                             _INSTALLED_MODULE_NAME + ".py")

    try:
        src_abs  = os.path.normcase(os.path.abspath(source_path))
        dest_abs = os.path.normcase(os.path.abspath(dest_path))
    except Exception:
        src_abs = dest_abs = ""

    if src_abs and src_abs != dest_abs:
        shutil.copy2(source_path, dest_path)
        print("[FBX PRO] copied script -> {}".format(dest_path))
    else:
        print("[FBX PRO] script already at {}".format(dest_path))

    # Make scripts_dir importable NOW so the shelf button works without a
    # Maya restart. Also evict any cached older copy of the module.
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    sys.modules.pop(_INSTALLED_MODULE_NAME, None)

    return dest_path


def _dragdrop_install_icon():
    """Decode the embedded PNG and write it to Maya's user bitmaps folder.

    That folder is on Maya's icon search path, so the shelf button can
    reference the icon by absolute path without any PATH gymnastics.

    Returns the absolute path to the installed icon, or None on failure
    (in which case we fall back to a built-in Maya icon).
    """
    import base64
    try:
        bitmaps_dir = cmds.internalVar(userBitmapsDir=True)
        if not os.path.isdir(bitmaps_dir):
            os.makedirs(bitmaps_dir)
        icon_path = os.path.join(bitmaps_dir, _ICON_FILE_NAME)
        with open(icon_path, "wb") as f:
            f.write(base64.b64decode(_ICON_B64))
        print("[FBX PRO] icon   -> {}".format(icon_path))
        return icon_path.replace("\\", "/")
    except Exception as e:
        cmds.warning("[FBX PRO] Couldn't write icon: {}".format(e))
        return None


def _dragdrop_install_shelf_button(icon_path=None):
    """Add (or replace) the shelf button on the currently active shelf."""
    shelf_top = mel.eval(
        "global string $gShelfTopLevel; $tmp=$gShelfTopLevel;")
    if not shelf_top or not cmds.tabLayout(shelf_top, exists=True):
        cmds.warning("[FBX PRO] Shelf UI not available; button not added.")
        return None

    current_shelf = cmds.tabLayout(shelf_top, query=True, selectTab=True)
    if not current_shelf:
        cmds.warning("[FBX PRO] No active shelf to add the button to.")
        return None

    # Remove any previous FBX PRO button so re-installs don't stack.
    existing = cmds.shelfLayout(current_shelf, query=True,
                                childArray=True) or []
    for btn in existing:
        try:
            if not cmds.shelfButton(btn, exists=True):
                continue
            if cmds.shelfButton(btn, query=True, label=True) == \
                    _SHELF_BUTTON_LABEL:
                cmds.deleteUI(btn)
        except Exception:
            pass

    # Use the custom icon if available; fall back to a built-in Maya icon
    # plus text overlay so the button is still identifiable.
    if icon_path and os.path.isfile(icon_path):
        cmds.shelfButton(
            parent=current_shelf,
            label=_SHELF_BUTTON_LABEL,
            annotation="Batch FBX Exporter PRO — Lila Games",
            image=icon_path,
            sourceType="python",
            command=_SHELF_BUTTON_COMMAND,
        )
    else:
        cmds.shelfButton(
            parent=current_shelf,
            label=_SHELF_BUTTON_LABEL,
            annotation="Batch FBX Exporter PRO — Lila Games",
            image="pythonFamily.png",
            imageOverlayLabel="FBX",
            overlayLabelColor=(0.95, 0.95, 0.95),
            overlayLabelBackColor=(0, 0, 0, 0.5),
            sourceType="python",
            command=_SHELF_BUTTON_COMMAND,
        )

    # Persist so the button survives a Maya restart.
    try:
        mel.eval('saveAllShelves $gShelfTopLevel;')
    except Exception:
        pass

    return current_shelf


def onMayaDroppedPythonFile(obj=None):
    """Entry point Maya calls when this .py file is dragged onto the viewport."""
    try:
        source_path = __file__
    except NameError:
        cmds.warning("[FBX PRO] Couldn't locate dropped script path. "
                     "Copy this file into your Maya scripts folder manually.")
        return

    try:
        _dragdrop_copy_to_scripts(source_path)
    except Exception as e:
        cmds.error("[FBX PRO] Copy failed: {}".format(e))
        return

    icon_path = _dragdrop_install_icon()
    shelf = _dragdrop_install_shelf_button(icon_path=icon_path)

    msg = ("<hl>Batch FBX Exporter PRO installed.</hl> "
           "Click the '{}' button on your shelf to launch.".format(
               _SHELF_BUTTON_LABEL))
    try:
        cmds.inViewMessage(amg=msg, pos='midCenter', fade=True,
                           fadeStayTime=3500, dragKill=True)
    except Exception:
        pass
    print("[FBX PRO] install complete"
          + (" (shelf: {})".format(shelf) if shelf else ""))