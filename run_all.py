from src.generate_data import generate_all
from src.build_database import build_database
from src.run_analysis import run_analysis


def main():
    generate_all()
    build_database()
    run_analysis()


if __name__ == "__main__":
    main()
