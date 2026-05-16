import os
import tempfile
from fastapi import APIRouter, UploadFile, File
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client

router = APIRouter()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")



####################################################################################
@router.post("/upload-policy")
async def upload_policy(institution_id: str, file: UploadFile = File(...)):
    # save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # load and chunk
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    chunks = splitter.split_documents(docs)

    # add institution_id to every chunk's metadata
    for chunk in chunks:
        chunk.metadata["institution_id"] = institution_id

    # embed and store in Supabase pgvector
    SupabaseVectorStore.from_documents(
        chunks,
        embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents"
    )

    os.unlink(tmp_path)
    return {"status": "success", "chunks_stored": len(chunks)}

#####################################################################################