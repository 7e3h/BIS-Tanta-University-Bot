from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

# Import shared data and logger
from utils.shared_data import user_sessions
from utils.logger import log_request

async def handle_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the logout button press."""
    user = update.effective_user
    log_request(user.id, user.username, "Logout Request")
    
    # Remove user session
    if user.id in user_sessions:
        user_data = user_sessions[user.id]
        del user_sessions[user.id]
        log_request(
            user.id, 
            user.username, 
            "Logout Success", 
            "SUCCESS",
            data={"ssn": user_data['ssn']}
        )
    else:
        log_request(user.id, user.username, "Logout - No Active Session", "INFO")
    
    # Remove keyboard and send goodbye message
    await update.message.reply_text(
        "✅ تم تسجيل الخروج بنجاح\n"
        "👋 شكراً لاستخدامك البوت\n"
        "يمكنك الضغط على /start للعودة مرة أخرى",
        reply_markup=ReplyKeyboardRemove()
    ) 