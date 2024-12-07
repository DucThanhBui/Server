from langchain.document_loaders import PyMuPDFLoader
from llama_index.readers import file
import pymupdf
from pprint import pprint
from summarize_agent import summarize

filename = "Thôn Tám Mộ.epub"
filename2 = "Bốc án.epub"
filename3 = "Ác Ý - Higashino Keigo.epub"
filename4 = "Mua La Rung Trong Vuon - Ma Van Khang.epub"

def getDicOfChapterContent(filePath: str):
    doc3 = pymupdf.Document(filePath)
    pprint(doc3.get_toc())

    loader = PyMuPDFLoader(filePath)
    documents = loader.load_and_split()
    #from pprint import pprint
    # pprint(documents)


    chapter_content = {}
    chapter_list = doc3.get_toc()

    def check(long: str, short: str) -> bool:
        l = long[:len(short) + 4]
        _short = short.split()
        # pprint(_short)
        for _s in _short:
            if _s not in l:
                return False
        return True

    current_document = 0
    for i in range(len(chapter_list)-1):
        key = chapter_list[i][1]
        # print("-------------------------------------------------------------------")
        # print(f'key is {key}')
        nextKey = chapter_list[i+1][1]
        # print(f'nextkey is {nextKey}')
        content = ""
        while (current_document < len(documents) and not check(documents[current_document].page_content, key)):
            current_document += 1
        while(current_document < len(documents) and not check (documents[current_document].page_content, nextKey)):
            content += documents[current_document].page_content
            current_document += 1

        # print(f'content is {content}')
        # print("-------------------------------------------------------------------")
        chapter_content[key] = content
        chapter_content[f"{key}_smrz"]=""

    chapter_content[chapter_list[-1][1]] = ""
    chapter_content[f"{chapter_list[-1][1]}_smrz"] = ""
    while current_document < len(documents):
        chapter_content[chapter_list[-1][1]] += documents[current_document].page_content
        current_document += 1

    # pprint(chapter_content)
    return chapter_content
