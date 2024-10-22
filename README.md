# Feedback Analyzer

**AI-Powered Feedback Extraction and Sentiment Analysis System**

## Overview

The Feedback Analyzer is an AI-powered system designed to extract text feedback from images and analyze sentiment to improve organizational response times. This project utilizes deep learning techniques and advanced natural language processing to efficiently categorize feedback and facilitate communication among relevant teams.

## Technologies

- **Python**
- **Flask**
- **OpenCV**
- **Deep Learning**
- **LangChain**
- **Large Language Model (LLM)**

## Features

- **REST API**: Extracts text feedback from over **1,000 images** posted on various platforms.
- **Sentiment Analysis**: Analyzes feedback text for sentiment and categorizes it.
- **Real-Time Processing**: Sends categorized feedback to the relevant team within **5 seconds**.
- **Enhanced Accuracy**: Implements Retrieval-Augmented Generation (RAG) to improve output accuracy by **15%**.

## Getting Started

### Prerequisites

- Python 3.x
- Flask
- OpenCV
- Required libraries can be installed using pip. See the `requirements.txt` file for a complete list.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/feedback-analyzer.git
1. Navigate to the project directory:

   ```bash
   cd feedback-analyzer
1. Install the required packages:

   ```bash
   pip install -r requirements.txt
1. Start the Flask server:

   ```bash
   python app.py
## Accessing the API

Access the API at [http://localhost:5000](http://localhost:5000).

## Usage

Send a POST request to the `/extract-feedback` endpoint with the image data to extract and analyze feedback.

### Example Request

```bash
curl -X POST -F 'image=@path_to_image.jpg' http://localhost:5000/extract-feedback
```
### Example Response

```bash
{
  "sentiment": "positive",
  "category": "Customer Service",
  "response_time": "2 seconds"
}
```
## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bugs. 

**Note**: This project is ongoing and not yet finished. Your input and suggestions are valuable as we continue to develop and improve the system.
