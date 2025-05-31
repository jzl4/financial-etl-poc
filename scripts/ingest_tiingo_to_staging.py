import sys
import os

current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
dotenv_path = os.path.join(project_root_folder, ".env")

print(__file__)
print(current_folder)
print(os.path.join(current_folder, ".."))
print(project_root_folder)
print(dotenv_path)

sys.path.append(project_root_folder)
print(sys.path)

# if __name__ == "__main__":
#     print(dotenv_path)