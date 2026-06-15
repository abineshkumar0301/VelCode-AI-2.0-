# VelCode - AI Integrated IDE

VelCode is an AI-powered desktop Integrated Development Environment (IDE) built to improve developer productivity through intelligent code assistance, voice interaction, and a modern development workflow.

The application combines a traditional code editor with local AI capabilities, allowing developers to generate code, explain logic, debug issues, and interact using natural language or voice commands without relying on cloud services.

## Features

* AI-powered code generation and assistance
* Local LLM integration using DeepSeek Coder 1.3B
* Voice-to-text coding commands using Faster Whisper
* Text-to-speech AI responses
* Syntax highlighting for Python, Java, and C++
* Smart auto-indentation
* Multi-tab code editor
* Integrated terminal
* File explorer and project navigation
* Dark and light themes
* Context-aware AI conversations
* Code explanation and debugging support
* Local-first architecture

## Tech Stack

### Frontend

* PyQt6

### Backend

* Python

### AI Components

* DeepSeek Coder 1.3B
* llama-cpp-python
* Faster Whisper

### Voice Technologies

* Speech-to-Text (Whisper Small)
* Text-to-Speech (pyttsx3)

### Development Tools

* Git
* GitHub

## Architecture

VelCode consists of two primary modules:

### IDE Core

Responsible for:

* Code editing
* Syntax highlighting
* Auto-indentation
* File management
* Terminal integration
* Theme management
* Project navigation

### AI Bridge

Responsible for:

* Local LLM communication
* Prompt construction
* Context management
* AI response processing
* Code extraction and insertion

## Supported Languages

* Python
* Java
* C++

## Project Structure

```text
VelCode/
│
├── VelCode_Final.py      # Main IDE application
├── ai_bridge.py          # AI communication layer
├── models/               # AI models (not included)
├── assets/
└── README.md
```

## Model Files

The AI model files are not included in this repository because GitHub file size restrictions prevent uploading large model weights.

Required models:

* DeepSeek Coder 1.3B GGUF
* Whisper Small CT2 Model

Download the models separately and update the local paths inside the project before running.

## Installation

```bash
git clone https://github.com/your-username/VelCode.git

cd VelCode

pip install -r requirements.txt
```

## Run

```bash
python VelCode_Final.py
```

## Motivation

Most lightweight code editors lack intelligent assistance, while many AI coding tools depend heavily on cloud services.

VelCode was developed to provide a local AI-powered development environment that combines coding, debugging, code generation, and voice interaction within a single desktop application.

## Future Enhancements

* Multi-language AI support
* Code completion engine
* Plugin ecosystem
* Project-wide code analysis
* AI-assisted refactoring
* Model switching support
* Real-time shared Coding

## Author

Abinesh Kumar

Developed as a final-year project focused on Artificial Intelligence and Software Development.
