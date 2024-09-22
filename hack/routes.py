import os
from flask import request, jsonify, send_file
from hack import app,db,bcrypt
from hack.tables import User, Pdf
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from hack.utils import save_pdf
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
import pymupdf
import llama_cpp
import uuid

client = QdrantClient(host="localhost", port=6333)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    length_function=len,
    is_separator_regex=False
)

embedding_model = llama_cpp.Llama(
    model_path="./models/bge-small-en-v1.5-f16.gguf",
    embedding=True,
    verbose=False
)

llm = llama_cpp.Llama(
    model_path="./models/Main-Model-7.2B-Q5_K_M.gguf",
    verbose=False
)

template = """
You are a helpful assistant who answers questions using the provided context. If you don't know the answer, 
simply state that you don't know.

{context}

Question: {question}"""


def pdf_to_documents(arr_docs):
    text = ""
    for doc in arr_docs:
        # Extract all the text from the pdf document
        for page in doc:
            result = page.get_text()
            text += result

    return text_splitter.create_documents([text])


def generate_doc_embeddings(_documents):
    local_document_embeddings = []
    # Generate Embeddings for every single document in documents and append it into document_embeddings
    for document in _documents:
        embeddings = embedding_model.create_embedding([document.page_content])
        local_document_embeddings.extend([
            (document, embeddings["data"][0]["embedding"])
        ])

    return local_document_embeddings


def insert_in_db(_document_embeddings):
    # If collection VectorDB exists then delete
    if client.collection_exists(collection_name="VectorDB"):
        client.delete_collection(collection_name="VectorDB")

    client.create_collection(
        collection_name="VectorDB",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings,
            payload={
                "text": document.page_content
            }
        )
        for document, embeddings in _document_embeddings
    ]

    operation_info = client.upsert(
        collection_name="VectorDB",
        wait=True,
        points=points
    )

    print("\n")
    print("operation_info: ")
    print(operation_info)


def query(_search_query):
    query_vector = embedding_model.create_embedding(_search_query)['data'][0]['embedding']
    search_result = client.search(
        collection_name="VectorDB",
        query_vector=query_vector,
        limit=3
    )

    print("\n")
    print("search_result: ")
    print(search_result)

    ans = llm.create_chat_completion(
        messages=[
            {"role": "user", "content": template.format(
                context="\n\n".join([row.payload['text'] for row in search_result]),
                question=_search_query
            )}
        ]
    )
    ans = ans['choices'][0]['message']['content']
    print(ans)
    return ans
    # for chunk in stream:
    #     ans = chunk['choices'][0]['delta'].get('content', '')
    #     yield ans

def insert_pdf_vectordb(_arr_docs):
    documents = pdf_to_documents(_arr_docs)

    document_embeddings = generate_doc_embeddings(documents)

    insert_in_db(document_embeddings)

token = "null"

@app.route('/question', methods=['POST'])
def question():
    if request.is_json:
        data = request.get_json()
        search_query = data.get("question")
        ans = query(search_query)
        return jsonify({"answer": ans})

    else:
        return jsonify({"error" : "Request must be JSON"})


@app.route('/selected', methods=['POST'])
def select_pdf():
    if request.is_json:
        data = request.get_json()

        name_arr = data.get("selected_pdf_names")
        pdf_file_array = []

        for pdf_name in name_arr:
            pdf_file = pymupdf.open("./hack/pdf_files/{}".format(pdf_name))
            pdf_file_array.append(pdf_file)

        insert_pdf_vectordb(pdf_file_array)
        return jsonify({'message': 'All PDF selected successfully'})

    else:
        return jsonify({"error" : "Request must be JSON"})


@app.route('/registration', methods=['POST'])
def registration():
    if request.is_json:
        data = request.get_json()

        user_name = data.get('username')
        if User.query.filter_by(username=user_name).first():
            return jsonify({'error': 'This username is taken'})

        email_add = data.get('email')
        if User.query.filter_by(email=email_add).first():
            return jsonify({'error': 'Email already exist'})

        hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        user = User(username=user_name, email=email_add, password=hashed_password)
        with app.app_context():
            db.session.add(user)
            db.session.commit()

        return jsonify({'message' : 'Successfully Registered'})

    else:
        return jsonify({"error": "Request must be JSON"}), 400


@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()

        email_add = data.get('email')
        pass_word = data.get('password')
        user = User.query.filter_by(email=email_add).first()
        if not user:
            return jsonify({"error": "Email is not registered"})
        if bcrypt.check_password_hash(user.password, pass_word):
            access_token = create_access_token(identity={'username': user.username,
                            'email': user.email, 'user_id': user.id})
            global token
            token = access_token
            return jsonify({"message": "Login successful",  "access_token": access_token})
        else:
            return jsonify({"error": "Invalid Password"})

    else:
        return jsonify({"error": "Request must be JSON"}), 400


@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({'error': "pdf file not found"})

    pdf_array = request.files.getlist('pdf_file')

    current_user = get_jwt_identity()
    user_id = current_user['user_id']

    for pdf in pdf_array:
        actual_name = pdf.filename
        pdf_name = save_pdf(pdf)
        user_pdf = Pdf(pdf_name=pdf_name, actual_pdf_name=actual_name, user_id=user_id)
        with app.app_context():
            db.session.add(user_pdf)
            db.session.commit()
    return jsonify({'message': 'All PDF uploaded successfully'})


@app.route('/download/<int:file_id>')
def get_pdf(file_id):
    pdf = Pdf.query.get(file_id)
    if pdf:
        name = pdf.pdf_name
        actual_name = pdf.actual_pdf_name
        path = os.path.join(app.root_path, 'pdf_files', name)

        return send_file(path_or_file=path, as_attachment=True,
                         download_name= str(actual_name),mimetype='application/pdf')

    return jsonify({"error" : 'file not found'})


@app.route('/delete/<int:file_id>')
def delete_pdf(file_id):
    pdf = Pdf.query.get(file_id)
    if pdf:
        file_name = pdf.pdf_name
        path = os.path.join(app.root_path, 'pdf_files', file_name)
        os.remove(path)
        db.session.delete(pdf)
        db.session.commit()
        return jsonify({"message" : "File deleted successfully"})

    return jsonify({"error" : 'file not found'})


@app.route('/history')
@jwt_required()
def history():
    json_obj = [ ]

    current_user = get_jwt_identity()
    user_id = current_user['user_id']

    pdfs = Pdf.query.filter_by(user_id=user_id).order_by(Pdf.date_posted.desc())
    if not pdfs:
        return jsonify({"message" : "No Pdf uploaded yet"})

    for p in pdfs:
        obj = {'pdf_id' : p.id, 'pdf_name' : p.actual_pdf_name,
               'date_posted' : p.date_posted.strftime('%d-%m-%Y'),
               'db_pdf_name' : p.pdf_name}
        json_obj.append(obj)

    return jsonify({'history' : json_obj})


@app.route('/logout')
@jwt_required()
def logout():
    current_user = get_jwt_identity()
    user_name = current_user['username']
    global token
    token = "null"
    return jsonify({'message': '{} is logged out'.format(user_name)})


@app.route('/account')
def account():
    return jsonify({"token" : token})
