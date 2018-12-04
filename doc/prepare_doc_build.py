import os
from shutil import copyfile
import platform

dirs = [
    "..",
]


def get_temp_dir(dirname):
    folder = os.path.split(dirname)[-1]
    if folder == "..":
        return os.path.join("source", ".tmp")
    else:
        return os.path.join("source", os.path.split(dirname)[-1], ".tmp")


if __name__ == "__main__":
    # =======================
    # Create .tmp directories
    # =======================
    print("Creating .tmp dirs:")
    for item in dirs:
        tmpDir = get_temp_dir(item)
        print(" - Creating %s" % tmpDir)
        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)

    # ============================
    # Move .rst files to .tmp dirs
    # ============================
    print("Moving .rst files into .tmp dirs:")
    for directory in dirs:
        for file in os.listdir(directory):
            if file.endswith(".rst"):
                source = os.path.join(directory, file)
                dest = os.path.join(get_temp_dir(directory), file)
                print(" - copying %s into %s" % (source, dest))
                copyfile(source, dest)
