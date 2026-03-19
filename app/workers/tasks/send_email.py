from fastapi_mail import FastMail, MessageSchema
from app.core.config import conf
from app.schemas.job import EmailPayload
async def send_email(payload:EmailPayload):
    message = MessageSchema(
        subject=payload.subject,
        recipients=[payload.to],
        body=payload.body,
        subtype= "html" if payload.is_html else "plain"
    )
    try:
      fm = FastMail(conf)
      await fm.send_message(message)
      return {"status": "success", "message": 'Email sent successfully'}
    except Exception as e:
        return {f"status": "failed" , "message": f"{str(e)}"}
    
    