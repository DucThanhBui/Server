from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Body, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from uuid import uuid4
import motor.motor_asyncio
from contextlib import asynccontextmanager
from search_explain import search, load_and_storage
from summarize_agent import summarize
from summary_text import getDicOfChapterContent
from translate import ContextualLlamaTranslator
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to execute at startup
    print("Server is starting!")
    await initialize_database()
    yield  # This point marks when the server starts accepting requests
    # Code to execute at shutdown
    print("Server is shutting down!")
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)

# Directory to store uploaded files
UPLOAD_DIR = "uploads"

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# MongoDB connection setup
MONGO_DETAILS = "mongodb://localhost:27017/"  # Change to your MongoDB URI
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
db = client.file_management  # Database name

# Models
class UserCreate(BaseModel):
    username: str
    password: str

class BookMark(BaseModel):
    creation: str  = None
    resourceIndex: str 
    bookId: str 
    resourceHref: str
    resourceType: str
    resourceTitle: str
    location: str
    locatorText: str

class HighLight(BaseModel):
    bookId: str
    tint: int = 0
    href: str
    type: str
    title: str = None
    text: str
    location: str
    totalProgression: str = "0" #double
    #location, text
    annotation: str = ""

class FileInfo(BaseModel):
    creation: str #long
    filename: str
    identifier: str = None
    username: str = None
    pathOnServer: str = None
    author: str = None
    progression: str = None
    rawMediaType: str
    bookmarks: list[BookMark]
    highlights: list[HighLight]
    cover: str = None

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

bookContent: dict = {}

# Dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    user = await get_user(token)
    if not user:
        return {"status: -1", "message: Invalid User"}
    return token

async def initialize_database():
    print("Initializing the database...")

async def cleanup_resources():
    print("Cleaning up resources...")

# Endpoints
@app.post("/register")
async def register(user: UserCreate):
    existing_user = await get_user(user.username)
    if existing_user:
        return {"status": -1, "msg": "Username already exists"}
    
    hashed_password = await hash_password(user.password)
    new_user = {"username": user.username, "hashed_password": hashed_password}
    await db.users.insert_one(new_user)
    
    return {"status": 0, "msg": "User registered successfully"}



@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    username = await authenticate_user(form_data.username, form_data.password)
    if not username:
        return {"status": -1, "msg": "Wrong username/ password"}
    return {"status": 0, "msg": "Login successfully", "access_token": username}



@app.post("/change-password")
async def change_password(
    current_password: str = Form(...), 
    new_password: str = Form(...), 
    username: str = Depends(get_current_user)
):
    user = await get_user(username)
    if not await verify_password(current_password, user["hashed_password"]):
        return {"status": -1, "msg": "Incorrect password"}
    
    hashed_password = await hash_password(new_password)
    await db.users.update_one({"username": username}, {"$set": {"hashed_password": hashed_password}})
    return {"status": 0, "msg": "Password changed successfully"}



@app.post("/upload")
async def upload_file(
    file: UploadFile
):
    file_path  = os.path.join(UPLOAD_DIR, file.filename)
    print(f"filepath is {file_path}")
    if os.path.exists(file_path):
        return {"status": -2, "msg": file_path}
    #cover_path = os.path.join(UPLOAD_DIR, cover.filename)
    try:
        # Save the uploaded `file` to the server directory
        file_content = await file.read()  # Read the file content once
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        print("success write file")
        
        return {
            "status": 0,
            "msg": file_path
        }
        
    except Exception as e:
        # Delete file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"status":-1, "msg": str(e)}

@app.post("/upload-info")
async def uploadInfo(
    fileInfo: FileInfo,
    current_user: str = Depends(get_current_user)               
):
    fileInfo.username = current_user
    print("fileInfo upto server")
    print(fileInfo)
    file_data = fileInfo.dict()
    print("data insert to database")
    print(file_data)

    # Insert file information into the database
    await db.files.insert_one(file_data)
    print("success insert data")

    filePath = fileInfo.pathOnServer
    fileName = os.path.splitext(os.path.basename(filePath))[0]

    load_and_storage(fileName)
    print(f"load_and_storage from fileName: {fileName}")
    dic = getDicOfChapterContent(filePath)
    for key in dic.items():
        print (key)
    bookContent[fileName] = dic
    
    return {"status": 0, "msg": "insert file info success"}

@app.get("/files", response_model=list[FileInfo])
async def list_files(
    current_user: str = Depends(get_current_user)
):
    user_files = await db.files.find({"username": current_user}).to_list(None)
    # for file in user_files:
    #     if file
    return [FileInfo(**file) for file in user_files]




@app.get("/file", response_model=FileInfo)
async def get_file(
    identifier: str, 
    current_user: str = Depends(get_current_user)
):
    file_info = await db.files.find_one({"username": current_user, "identifier": identifier})
    if not file_info:
        return {"status": -1, "msg":"File not found"}
    
    return FileInfo(**file_info)



@app.patch("/update-file")
async def update_file(
    update_data: FileInfo,
    current_user: str = Depends(get_current_user)
):
    update_data.username = current_user
    update_data_fomarted = update_data.dict()
    result = await db.files.update_one({"username": current_user, "identifier": update_data.identifier}, {"$set": update_data_fomarted})
    if result.matched_count == 0:
        return {"status": -1, "msg": "File not found"}
    
    return {"status": 0, "msg": "File info updated"}




@app.delete("/delete")
async def delete_file( 
    identifier: str, 
    current_user: str = Depends(get_current_user)
):
    file_info = await db.files.find_one({"username": current_user, "identifier": identifier}) 
    if not file_info:
        return {"status": -1, "msg":"File not found"}
        
    # Delete the file from storage
    if os.path.exists(file_info["pathOnServer"]):
        os.remove(file_info["pathOnServer"])
        print("deleted epub")
    if os.path.exists(file_info["cover"]):
        os.remove(file_info["cover"])
        print("deleted cover")
    
    # Delete the database entry
    await db.files.delete_one({"username": current_user, "identifier": identifier})
    
    return {"status": 0, "msg": "File deleted successfully"}

@app.get("/summarize")
async def getSummarize(
    idf: str,
    chapterName: str
):
    
    print(f"chapterNAme ------ is {chapterName}")
    file_info = await db.files.find_one({"identifier": idf})
    if not file_info:
        return {"status": -1, "msg":"File not found"}
    fileInfo = FileInfo(**file_info)
    filePath = fileInfo.pathOnServer
    fileName = os.path.splitext(os.path.basename(filePath))[0]
    content = bookContent[fileName]
    chapter_content = content[chapterName]
    print(f"chapter content is: {chapter_content}")
    page_smrz  = content[f"{chapterName}_smrz"]
    if (page_smrz is not None and len(page_smrz) > 10): 
        return {"status": 0, "msg": page_smrz}
    response = summarize(text=chapter_content, detail=0.75, verbose=True, model="gpt-4o-mini")
    content[f"{chapterName}_smrz"] = response
    print(f"summary: {response}")
    return {"status": 0, "msg": response}

@app.post("/translate")
async def getTranslate(
    text: str,
    before: str,
    after: str,
    src_lang: str,
    des_lang: str
):
    agent = ContextualLlamaTranslator()
    response = agent.translate(before, text, after, src_lang, des_lang)
    return {"status": 0, "msg": response}

@app.post("/search")
async def getSearch(
    idf: str,
    input: str
):
    file_info = await db.files.find_one({"identifier": idf})
    if not file_info:
        return {"status": -1, "msg":"File not found"}
    fileInfo = FileInfo(**file_info)
    filePath = fileInfo.pathOnServer
    fileName = os.path.splitext(os.path.basename(filePath))[0]
    response = search(fileName=fileName, input=input)
    return {"status": 0, "msg": response}

# Utility functions
async def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

async def get_user(username: str) -> UserCreate:
    return await db.users.find_one({"username": username})

async def authenticate_user(username: str, password: str) -> Optional[str]:
    user = await get_user(username)
    if user and await verify_password(password, user["hashed_password"]):
        return username
    return None