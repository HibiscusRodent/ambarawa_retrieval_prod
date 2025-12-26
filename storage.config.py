import __main__
from dask.dot import name
import lancedb
import Pathlib
import os




# ------ input files
def inputFiles():
    sample_data_paths = "./sample_data"
    sample_book_one = os.path.join(sample_data_paths, "rak-0018_baris-002_buku-12")
    sample_book_two = os.path.join(sample_data_paths, "rak-0003_baris-005_buku-30")
    return None
    
    
    


#--- output files
output_data_path = "./data/output_book_data"


def main() -> None:
    return None

if __name__ == "__main__":
    main()