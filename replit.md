# replit.md

## Overview

The Shakespeare Club Communication App is a web-based platform designed for Sir Isaac Newton College of Engineering and Technology to enhance students' communication skills through structured practice modules. The application provides different types of communication exercises (listening, observation, speaking, and writing) with AI-powered analysis and feedback using Google's Gemini API. Students can register, complete practices, track their progress, and view performance rankings, while administrators can manage students and create new practice modules.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templating with Flask for server-side rendering
- **UI Framework**: Bootstrap 5.1.3 for responsive design and styling
- **JavaScript**: Vanilla JavaScript for client-side interactions including form validation, auto-hiding alerts, and practice submission handling
- **Styling**: Custom CSS with gradient backgrounds, card-based layouts, and hover effects

### Backend Architecture
- **Web Framework**: Flask application with session-based authentication
- **Route Structure**: Separate routes for student and admin functionalities with role-based access control
- **Authentication**: Session-based authentication with password hashing using Werkzeug security utilities
- **Practice System**: Four types of communication practices (listening, observation, speaking, writing) with structured submission and analysis workflow

### Data Storage
- **Database**: SQLite database with four main tables:
  - `students`: User registration and profile information
  - `admins`: Administrator accounts
  - `practices`: Practice modules with type, content, and metadata
  - `student_performances`: Practice submissions with scores and analysis results
- **File Storage**: Practice content files stored in the file system

### AI Integration
- **Gemini API**: Google Gemini 2.5 models for communication analysis
- **Sentiment Analysis**: Uses Gemini Pro model to analyze communication quality with 1-5 star ratings and confidence scores
- **Text Summarization**: Uses Gemini Flash model for content summarization
- **Response Analysis**: Structured analysis of student practice submissions with JSON response formatting

### Security Features
- **Password Security**: Werkzeug password hashing for secure credential storage
- **Session Management**: Flask session handling with configurable secret keys
- **Input Validation**: Client-side and server-side form validation
- **Role-based Access**: Separate authentication flows for students and administrators

## External Dependencies

### Third-party APIs
- **Google Gemini API**: AI-powered text analysis and communication assessment
  - Models: gemini-2.5-flash, gemini-2.5-pro
  - Features: Sentiment analysis, text summarization, communication practice evaluation

### Frontend Libraries
- **Bootstrap 5.1.3**: CSS framework for responsive UI components
- **Bootstrap JavaScript Bundle**: Client-side component functionality

### Python Packages
- **Flask**: Web application framework
- **Werkzeug**: Security utilities for password hashing
- **google-genai**: Google Gemini API client library
- **Pydantic**: Data validation and parsing for API responses

### Development Tools
- **SQLite**: Embedded database for development and lightweight deployment
- **Jinja2**: Template engine integrated with Flask