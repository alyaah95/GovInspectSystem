GovInspect — Field Inspection System

GovInspect is a robust digital solution designed to transform traditional paper-based field inspection workflows into an efficient, streamlined digital process. It features role-based access control (RBAC), real-time reporting, and secure document archiving.

🚀 Live Demo

You can explore the live application hosted on Vercel:
🔗 GovInspect Live Link

🔑 Test Credentials

You can log in using the following pre-configured accounts depending on the role you wish to test:

Manager Account:

Username: hassan

Password: hassan.govinspect.eg

Inspector Account:

Username: alaa.atef

Password: alaa.govinspect.eg

🛠️ Built With

Backend: Python / Django

Frontend: Tailwind CSS

Database: PostgreSQL (Neon DB)

Media Storage: Cloudinary

💻 Getting Started Locally

If you want to run this project on your local machine, follow these steps:

1. Prerequisites

Make sure you have the following installed on your system:

Python (v3.8 or higher)

Git

PostgreSQL (or use a remote Neon DB URL)

2. Clone the Repository

git clone https://github.com/your-username/gov-inspect-system.git
cd gov-inspect-system


3. Create and Activate a Virtual Environment

# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate


4. Install Dependencies

pip install -r requirements.txt


5. Configure Environment Variables

Create a .env file in the root directory of your project and configure it using the template below (replace the placeholder values with your own credentials/database connection):

DATABASE_URL="your_postgresql_connection_string"
SECRET_KEY="your_django_secret_key"
EMAIL_HOST_USER="your_email@gmail.com"
EMAIL_HOST_PASSWORD="your_email_app_password"
CLOUDINARY_CLOUD_NAME="your_cloud_name"
CLOUDINARY_API_KEY="your_api_key"
CLOUDINARY_API_SECRET="your_api_secret"


6. Run Database Migrations

python manage.py migrate


7. Run the Development Server

python manage.py runserver


Open your browser and navigate to http://127.0.0.1:8000/ to view the application locally.
