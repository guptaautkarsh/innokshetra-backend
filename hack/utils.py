import os
import secrets
from hack import app

def save_pdf(pdf):
    random_hex = secrets.token_hex(8) #just to make file name unique
    f_name, f_ext = os.path.splitext(pdf.filename) #.filename to extract filename from the uploaded pic
    pdf_fn = random_hex + f_ext
    # now we need to get full path where this pdf will be stored
    save_pdf_path = os.path.join(app.root_path, 'pdf_files', pdf_fn)
    pdf.save(save_pdf_path) #save pdf to that path
    return pdf_fn #returning pdf name so we can use it to change in database

def save_pdf_to_documents(pdf):
    pdf_fn = pdf.filename
    save_pdf_path = os.path.join(app.root_path, 'MLmodel/project_convex/documents', pdf_fn)
    pdf.save(save_pdf_path) #save pdf to that path

# def clear_documents():
#     # delete all the existing files
#     folder_path = os.path.join(app.root_path, 'MLmodel/project_convex/documents')
#     if not os.listdir(folder_path):
#         return
#
#     for file_name in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, file_name)
#         os.remove(file_path)
