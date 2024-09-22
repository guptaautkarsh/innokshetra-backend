import os
import secrets
from hack import app

def save_pdf(pdf):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(pdf.filename)
    pdf_fn = random_hex + f_ext
    save_pdf_path = os.path.join(app.root_path, 'pdf_files', pdf_fn)
    pdf.save(save_pdf_path)
    return pdf_fn

def save_pdf_to_documents(pdf):
    pdf_fn = pdf.filename
    save_pdf_path = os.path.join(app.root_path, 'MLmodel/project_convex/documents', pdf_fn)
    pdf.save(save_pdf_path)

# def clear_documents():
#     # delete all the existing files
#     folder_path = os.path.join(app.root_path, 'MLmodel/project_convex/documents')
#     if not os.listdir(folder_path):
#         return
#
#     for file_name in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, file_name)
#         os.remove(file_path)
