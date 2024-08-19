from os import listdir, path

def get_file_lines(file_path: str) -> int:
    with open(file_path, "r") as doc:
        linu = sum(char == "\n" for char in doc.read()) + 1
    print(f"{linu:<6} in {file_path}")
    return linu

def get_accum_lines(pathstr: str, file_ext: str = ".py") -> int:
    elem_paths = [path.join(pathstr,pat) for pat in listdir(pathstr)]
    files = (pat for pat in elem_paths if not path.isdir(pat) and pat.endswith(file_ext))
    dirs = (pat for pat in elem_paths if path.isdir(pat))

    filelines = sum(get_file_lines(file) for file in files)
    dirlines = sum(get_accum_lines(dirpath, file_ext) for dirpath in dirs)
    return filelines + dirlines

if __name__ == "__main__":
    ext = ".py"
    print(f"> Zählt, wieviele Zeilen mit der Dateiendung {ext} in diesem Ordner liegen.")
    pylines = get_accum_lines(".", ext)
    print(pylines)