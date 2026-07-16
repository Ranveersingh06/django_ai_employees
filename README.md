# Django AI Employees

Django AI Employees is an AI-powered customer support platform built with **Django**, **Google Gemini**, and **ChromaDB**. It simulates customer support for a fictional air conditioner retailer, **CoolBreeze AC**, where an AI assistant named **Maya** helps customers with order tracking, refund requests, warranty inquiries, and policy-related questions.

The project demonstrates how **Large Language Models (LLMs)**, **Retrieval-Augmented Generation (RAG)**, and a **multi-agent architecture** can be integrated into a traditional Django application.

---

## Features

- AI-powered customer support using Google Gemini
- Multi-agent workflow (Support Agent, Manager Agent, Risk Agent)
- Retrieval-Augmented Generation (RAG) with ChromaDB
- Order tracking and delivery status lookup
- Refund request handling
- Fraud risk assessment
- Conversation history
- Django authentication and admin panel
- MySQL database
- Bootstrap-based frontend

---

## Architecture

```
Customer
    │
    ▼
Support Agent (Maya)
    │
    ├──► Knowledge Base (RAG)
    │
    └──► Manager Agent
              │
              ▼
        Risk Assessment Agent
              │
              ▼
        Final Response
```

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Django 6 |
| Database | MySQL |
| AI | Google Gemini |
| Vector Database | ChromaDB |
| PDF Processing | PyPDF |
| Frontend | HTML, CSS, Bootstrap |

---

## Project Structure

```text
django_ai_employees/
├── dj_ai_employees_main/
├── orders/
├── support/
├── templates/
├── chromadb/
├── manage.py
└── requirements.txt
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/Ranveersingh06/django_ai_employees.git
cd django_ai_employees
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
SECRET_KEY=your_secret_key
DEBUG=True

DB_NAME=your_database
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=3306

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Run migrations and load demo data:

```bash
python manage.py migrate
python manage.py loaddata orders/demo_data.json
python manage.py runserver
```

Visit:

```
http://127.0.0.1:8000/
```

---

## Demo Credentials

```
Username: rathan
Password: Root@123
```

---

## Example Questions

- Where is my order?
- Has my order been dispatched?
- Can I request a refund?
- Is my AC under warranty?
- What is your refund policy?
- How often should I service my AC?

---

## Future Improvements

- Docker support
- Redis and Celery integration
- Streaming AI responses
- REST API
- WebSocket-based chat
- Live shipment tracking

---

## Author

**Ranveer Singh**

GitHub: https://github.com/Ranveersingh06
