import os, gzip, hashlib

def file_hash(path, algo="sha256"):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def gz_content_hash(path, algo="sha256"):
    h = hashlib.new(algo)
    with gzip.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

dir1 = "/Users/valentinopapandrea/Downloads/inputData"
dir2 = "/Users/valentinopapandrea/Downloads/old data"

files = sorted(set(os.listdir(dir1)) & set(os.listdir(dir2)))

for f in files:
    p1, p2 = os.path.join(dir1, f), os.path.join(dir2, f)
    raw_equal = file_hash(p1) == file_hash(p2)
    content_equal = gz_content_hash(p1) == gz_content_hash(p2)

    print(f"{f}:")
    print(f"  🔹 compressed bytes equal? {'✅ yes' if raw_equal else '❌ no'}")
    print(f"  🔹 decompressed .nc content equal? {'✅ yes' if content_equal else '❌ no'}\n")


