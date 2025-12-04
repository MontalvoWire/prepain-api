from mangum import Mangum

from app import app as fastapi_app

# Entry point for Vercel's serverless runtime (AWS Lambda under the hood).
handler = Mangum(fastapi_app)
