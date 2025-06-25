from flask import Flask,render_template,url_for,request,redirect,session,jsonify
from werkzeug.utils import secure_filename
from flask_session import Session
import os
import pickle
import pymupdf
import faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chains import RetrievalQA
from langchain_huggingface import HuggingFacePipeline
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
UPLOAD_FOLDER='UPLOAD'
model = genai.GenerativeModel('gemini-1.5-flash')
retriever =None
file_path = "faiss_store.pkl"
ALLOWED_TYPE={'pdf'}
app=Flask(__name__)
app.config["SESSION_PERMANENT"] = False     # Sessions expire when browser closes
app.config["SESSION_TYPE"] = "filesystem"     # Store session data on the filesystem
Session(app)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///test.db'

with app.app_context():
    db=SQLAlchemy(app)
    class Chat(db.Model):
        id=db.Column(db.Integer,primary_key=True)
        file_name=db.Column(db.String(200),nullable=False)
        question=db.Column(db.String(200),nullable=False)
        answer=db.Column(db.String(200),nullable=False)
    def __repr__(self):
            return '<chat %r>' % self.id
    db.create_all()


@app.route('/',methods=['GET','POST'])
def index():
    response=""
    if(request.method=='GET'): 
        chats=Chat.query.order_by(Chat.id).all() 
      
        session["FILE_NAME"]=""
        session["FILE_UPLOAD_STATUS"]=False
        session["FILE_PROCESS_STATUS"]=False
        print("OVER HERE")
        return render_template('index.html',response="",chats=chats,processed=False)
    elif 'file' in request.files:
        uploaded=request.files['file']
        chats=Chat.query.order_by(Chat.id).all()
        if(uploaded.filename!=''):
            print(request.method)
            session["FILE_NAME"]=uploaded.filename
            uploaded.filename='content.pdf'
            filename=secure_filename(uploaded.filename)
            uploaded.save(os.path.join(UPLOAD_FOLDER, filename))
            session["FILE_UPLOAD_STATUS"]=True
            
            session["FILE_PROCESS_STATUS"]=False
            response=[]
            response.append(session.get("FILE_NAME"))
            chats=Chat.query.order_by(Chat.id).all()
            return render_template('index.html',response=response,chats=chats,processed=session.get("FILE_PROCESS_STATUS"))
        else:
            return render_template('index.html',error="No file uploaded",chats=chats)
    elif 'process' in request.form and session.get("FILE_UPLOAD_STATUS")==True:
  
        document=pymupdf.open('UPLOAD/content.pdf')
        content=""
        for page in document:
            content+=page.get_text()
        splitter=RecursiveCharacterTextSplitter(separators=["\n\n","\n"," "],chunk_size=500,chunk_overlap=50)
        chunks=splitter.split_text(content)
        embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        vector_db = FAISS.from_texts(chunks, embedding)
        with open(file_path, "wb") as f:
            pickle.dump(vector_db, f)
        two=True
        session["FILE_PROCESS_STATUS"]=True
        response=[]
        response.append(session.get("FILE_NAME"))
        chats=Chat.query.order_by(Chat.id).all()
        return render_template('index.html',response=response,chats=chats,processed=session.get("FILE_PROCESS_STATUS"))

    elif 'query' in request.form and session.get("FILE_PROCESS_STATUS")==True:
        if request.form['query']=="" or request.form['query']=='Ask query':
             chats=Chat.query.order_by(Chat.id).all()
             return render_template('index.html',file_name=session.get("FILE_NAME"),error="No query entered",chats=chats,processed=session.get("FILE_PROCESS_STATUS"))
        else:
            
            if os.path.exists(file_path):
                vectorstore=None
                with open(file_path, "rb") as f:
                    vectorstore = pickle.load(f)
                retriever = vectorstore.as_retriever()
                query=request.form['query']
                relevant_docs = retriever.get_relevant_documents(query)
                context = "\n\n".join([doc.page_content for doc in relevant_docs])
                prompt = f"Given:\n{context}\n\n Answer this Question(to the best of your ability with given context,answer it in plain text no styling):\n{query}"
                answer = model.generate_content(prompt,generation_config={"max_output_tokens": 300 })
                response=[]
                response.append(session.get("FILE_NAME"))
                response.append(answer.text)
                new_db_item=Chat(question=query,answer=answer.text,file_name=session.get("FILE_NAME"))
                try:
                    db.session.add(new_db_item)
                    db.session.commit()
                except:
                    return "Error loading to db"
                print("FILENAME IS ",session.get("FILE_NAME"))
                chats=Chat.query.order_by(Chat.id).all()
                return render_template('index.html',response=response,chats=chats,processed=session.get("FILE_PROCESS_STATUS"))
            else:
                return "Error loading vector database"
    else:
        chats=Chat.query.order_by(Chat.id).all()
        if(not session.get("FILE_UPLOAD_STATUS")):
           
            return render_template('index.html',error="No file uploaded",chats=chats,processed=session.get("FILE_PROCESS_STATUS"))
        elif(not session.get("FILE_PROCESS_STATUS")):
            error=[]
            error.append(session.get("FILE_NAME"))
            error.append("File Not Processed")
            print("HELLO \n\n\n",session.get("FILE_PROCESS_STATUS"))
            return render_template('index.html',error=error,chats=chats,processed=session.get("FILE_PROCESS_STATUS"))
@app.route('/delete/<int:id>',methods=['POST'])
def del_chat(id):
    item=Chat.query.get_or_404(id)
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success':True})
    except:
        return jsonify({'success':False})

if __name__=="__main__":
    app.run(debug=True)