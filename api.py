import re
import math
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import speech_recognition as sr
import wave
import openai
from fastapi.middleware.cors import CORSMiddleware


openai.api_key = ""

app = FastAPI()

# Allow all origins
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


product_knowledge_file_path = 'product_knowledge.txt'
with open(product_knowledge_file_path, 'r') as file:
    product_knowledge = file.read()

# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////// AUDIO 
class TranscribeAudio:
    @classmethod
    def get_duration_video_minutes(cls, path_to_media: str):
        with wave.open(path_to_media, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            duration_minutes = duration / 60
            return duration_minutes

    @classmethod
    def extract_script(cls, path_to_media: str, path_text: str):
        total_voice_in_min = math.ceil(cls.get_duration_video_minutes(path_to_media))
        sliced_total = math.ceil(total_voice_in_min / 2)

        r = sr.Recognizer()

        for i in range(sliced_total):
            with sr.AudioFile(path_to_media) as source:
                audio = r.record(source, duration=120, offset=i * 120)
            with open(path_text, "a") as f:
                text = r.recognize_google(audio, language="en-US")
        return text


def generate_summary(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "user", "content": f"""{prompt}"""}
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response


def get_product_knowledge_score(text):
    # Define prompt
    prompt_template = f"""
    1. Product Knowledge (1 to 10):
    On a scale from 1 to 10, rate the speaker's understanding and demonstration of product knowledge. Give the explanation also in new line 
    Please refer to the product knowledge catalog given compare it with the transcript.
    2. Sentiment:
    Describe the overall sentiment of the conversation as either good, neutral, or bad. Give the explanation also in new line 
    3. Suggestions for Improvement (Less than 30 words):
    Provide concise suggestions for improvement, focusing on specific areas that could enhance the communication. Give example for each suggestion you give

    Transcript: {text}
    Product Knowledge Catalog: {product_knowledge}

    Example of response format:
    1. Product Knowledge: 4
    The speaker mentions a specific product, the Hong Ying Banks growth opportunity fund, but does not provide any additional information or explanation about the product. It would be helpful for the speaker to provide more details and benefits of the product they are recommending.

    2. Sentiment: Neutral
    Based on the given transcript, the overall sentiment of the conversation appears to be neutral. There is no clear indication of a positive or negative tone.

    3. Suggestions for Improvement:
    - Provide more information about the recommended product, such as its features, benefits, and any potential risks or limitations. For example, the speaker could explain how the growth opportunity fund works, what kind of returns it has generated in the past, and how it aligns with the customer's specific investment goals.
    - Use clear and concise language to explain complex financial terms and concepts. Avoid assuming that the customer is already familiar with technical jargon. For example, instead of saying "tailor the strategy to align with your ambition," the speaker could say "customize the investment approach to align with your specific goals and aspirations."
    - Offer alternative options or suggestions based on the customer's needs and preferences. For example, the speaker could mention other investment funds or strategies that might also be suitable for an education
    """

    # get the score from the response
    res = generate_summary(prompt_template)
    return res['choices'][0]['message']['content']


# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////// PDF
def parse_feedback(feedback):
    # Define regular expressions for extracting values
    product_knowledge_pattern = re.compile(r'Product Knowledge: (\d+)')
    sentiment_pattern = re.compile(r'Sentiment: (\w+)')
    improvement_pattern = re.compile(r'Suggestions for Improvement:(.*)', re.DOTALL)

    # Extract values using regular expressions
    product_knowledge_match = product_knowledge_pattern.search(feedback)
    sentiment_match = sentiment_pattern.search(feedback)
    improvement_match = improvement_pattern.search(feedback)

    # Retrieve values or set default values if not found
    product_knowledge = int(product_knowledge_match.group(1)) if product_knowledge_match else None
    sentiment = sentiment_match.group(1) if sentiment_match else None
    suggestions_for_improvement = [s.strip() for s in improvement_match.group(1).split('-') if s.strip()] if improvement_match else None

    # Extract specific explanations
    product_knowledge_explanation = re.search(r'Product Knowledge: \d+\n(.+?)\n\n', feedback, re.DOTALL).group(1) if product_knowledge_match else None
    sentiment_explanation = re.search(r'Sentiment: \w+\n(.+?)\n\n', feedback, re.DOTALL).group(1) if sentiment_match else None

    return product_knowledge, sentiment, suggestions_for_improvement, product_knowledge_explanation, sentiment_explanation


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    with open("temp.wav", "wb") as audio_file:
        audio_file.write(file.file.read())

    script_extraction_response = TranscribeAudio.extract_script('temp.wav', 'temp.txt')
    res = get_product_knowledge_score(script_extraction_response)

    print("")
    print(res)

    product_knowledge, sentiment, suggestions_for_improvement, product_knowledge_explanation, sentiment_explanation = parse_feedback(res)

    response_data = {
        "Product_Knowledge": product_knowledge,
        "Product_Knowledge_Explanation": product_knowledge_explanation,
        "Sentiment": sentiment,
        "Sentiment_Explanation": sentiment_explanation,
        "Suggestions_for_Improvement": suggestions_for_improvement,
        "Transcription": script_extraction_response
    }

    return JSONResponse(content=response_data)


# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////// DOCUMENT 
from pydantic import BaseModel
from typing import List
from PyPDF2 import PdfReader
import io
# from tika import parser

# Parsing the guideline PDF
# parsed_pdf = parser.from_file('document_guidelines.pdf')
# guidelines_text = parsed_pdf['content'].strip()

class DocumentResponse(BaseModel):
    formatting_score: int
    comparison_score: int
    suggestions_for_improvement: List[str]
    formatting_explanation: str
    comparison_explanation: str

def extract_text_from_pdf(pdf_path):
    # creating a pdf reader object
    reader = PdfReader(pdf_path)

    # printing number of pages in pdf file
    num_pages = len(reader.pages)

    # initializing an empty string to store concatenated text
    all_text = ""

    # loop through all pages and extract text
    for page_num in range(num_pages):
        # getting a specific page from the pdf file
        page = reader.pages[page_num]

        # extracting text from page
        text = page.extract_text()

        # concatenate text from each page
        all_text += text

    return all_text

def get_document_score(guidelines_text, parsed_pdf):
    # Define prompt
    prompt_template = f"""
    1. Formatting (1 to 10):
    On a scale from 1 to 10, rate the document formatting on the title and the numbering and etc. Give the explanation also in new line 
    2. Comparison (1 to 10):
    On a scale from 1 to 10, rate the document's by comparing it to the benchmark wether it follow the guidelines or not. Give the explanation also in new line 
    Please refer to the guideline given compare it with the document.
    3. Suggestions for Improvement (Less than 30 words):
    Provide concise suggestions for improvement, focusing on specific areas that could enhance the document. Give example for each suggestion you give

    Document: {parsed_pdf}
    Guideline: {guidelines_text}

    Example of response format:
    1. Formatting: 4
    The speaker mentions a specific product, the Hong Ying Banks growth opportunity fund, but does not provide any additional information or explanation about the product. It would be helpful for the speaker to provide more details and benefits of the product they are recommending.

    2. Comparison: 6
    This example here

    3. Suggestions for Improvement:
    - Suggestion 1
    - Suggestion 2
    - Suggestion 3
    """

    # get the score from the response
    res = generate_summary(prompt_template)
    return res['choices'][0]['message']['content']

def parse_document_feedback(feedback):
    # Define regular expressions for extracting values
    formatting_pattern = re.compile(r'Formatting: (\d+)')
    comparison_pattern = re.compile(r'Comparison: (\d+)')
    improvement_pattern = re.compile(r'Suggestions for Improvement:(.*)', re.DOTALL)

    # Extract values using regular expressions
    formatting_match = formatting_pattern.search(feedback)
    comparison_match = comparison_pattern.search(feedback)
    improvement_match = improvement_pattern.search(feedback)

    # Retrieve values or set default values if not found
    formatting_score = int(formatting_match.group(1)) if formatting_match else None
    comparison_score = int(comparison_match.group(1)) if comparison_match else None
    suggestions_for_improvement = [s.strip() for s in improvement_match.group(1).split('-') if s.strip()] if improvement_match else None

    # Extract specific explanations
    formatting_explanation = re.search(r'Formatting: \d+\n(.+?)\n\n', feedback, re.DOTALL).group(1) if formatting_match else None
    comparison_explanation = re.search(r'Comparison: \d+\n(.+?)\n\n', feedback, re.DOTALL).group(1) if comparison_match else None

    return formatting_score, comparison_score, suggestions_for_improvement, formatting_explanation, comparison_explanation



@app.post("/analyze-pdf")
async def analyze_pdf(pdf_file: UploadFile = File(...)):
    try:
        # Parsing the guideline PDF using tika
        # parsed_pdf = parser.from_buffer(await pdf_file.read())
        guidelines_text = extract_text_from_pdf('document_guidelines.pdf')

        # Save the uploaded PDF as a temporary file
        temp_pdf_path = "temp.pdf"
        with open(temp_pdf_path, "wb") as temp_pdf:
            temp_pdf.write(await pdf_file.read())

        # Extracting text from the PDF using PyMuPDF
        parsed_pdf = extract_text_from_pdf(temp_pdf_path)


        # Get the document score
        document_res = get_document_score(guidelines_text, parsed_pdf)

        # Parse the feedback
        formatting_score, comparison_score, suggestions_for_improvement, formatting_explanation, comparison_explanation = parse_document_feedback(document_res)

        # Return the parsed values as JSON
        return JSONResponse(content={
            "Formatting Score": formatting_score,
            "Formatting Explanation": formatting_explanation,
            "Comparison Score": comparison_score,
            "Comparison Explanation": comparison_explanation,
            "Suggestions for Improvement": suggestions_for_improvement
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")