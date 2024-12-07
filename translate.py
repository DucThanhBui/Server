from llama_index.llms.openai import OpenAI
from llama_index.core.prompts import Prompt
from llama_index.core import Settings
import os



class ContextualLlamaTranslator:
    def __init__(self, model_name="gpt-4o-mini"):
        Settings.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), model=model_name, temperature=0)
        # Define a prompt template
        self.prompt_template = Prompt(
            template=(
            "You are a translator. Here is some context:\n"
            "Before text: {before_text}\n"
            "Highlight text: {highlight_text}\n"
            "After text: {after_text}\n\n"
            "Translate the highlighted text from {src_lang} into {des_lang} only. "
            "If {src_lang} is Auto, please auto detect source language"
            "Do not provide additional instructions or explanations.\n\n"
            "Translation:"
            )
        )

    def translate(self, before_text, highlight_text, after_text, src_lang, des_lang):
        # Format the prompt
        prompt_variables = {
            "before_text": before_text,
            "highlight_text": highlight_text,
            "after_text": after_text,
            "src_lang": src_lang,
            "des_lang": des_lang,
        }
        
        # Predict the response
        response = Settings.llm.predict(prompt=self.prompt_template, **prompt_variables)
        return str(response)

# Usage
if __name__ == "__main__":
    # Initialize the translator
    translator = ContextualLlamaTranslator()

    # Define translation parameters
    before_text = ""
    highlight_text = "请翻译以下这段文字：今天，我手写我心，记录生活点滴，是为了明天，再看回这些文字的时候能感动自己"
    after_text = ""
    source_language = "Auto"
    destination_language = "Vietnamese"

    # Get the translation
    translation = translator.translate(before_text, highlight_text, after_text, source_language, destination_language)
    print(f"Translated Text: {translation}")

    # Hãy dịch đoạn văn sau: 
    # Hôm nay, tôi viết tay trái tim mình và ghi lại từng khoảnh khắc của cuộc đời, 
    # để ngày mai đọc lại những dòng chữ này, tôi sẽ cảm động.