import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import time, datetime
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Store responses for each day {date: {user_id: response}}
daily_responses = {}

# Bot configuration - using environment variables for security
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "YOUR_GROUP_CHAT_ID")
TIMEZONE = pytz.timezone("Asia/Singapore")

async def send_daily_question(context: ContextTypes.DEFAULT_TYPE):
    """Send the daily feeding question"""
    from datetime import date
    
    # Reset responses for new day
    today = str(date.today())
    daily_responses[today] = {}
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data=f"yes_{today}")],
        [InlineKeyboardButton("⏰ Not yet but I will feed her today", callback_data=f"later_{today}")],
        [InlineKeyboardButton("❌ No, can someone feed her?", callback_data=f"no_{today}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🐾 **Daily Check: Have we fed John?**\n\nPlease select an option below:"
    
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    data = query.data
    
    # Parse the callback data
    action, date_str = data.rsplit('_', 1)
    
    # Store the response
    if date_str not in daily_responses:
        daily_responses[date_str] = {}
    
    response_text = {
        'yes': '✅ Yes',
        'later': '⏰ Not yet but I will feed her today',
        'no': '❌ No, can someone feed her?'
    }
    
    daily_responses[date_str][user.id] = {
        'name': user_name,
        'response': response_text[action]
    }
    
    # Build summary message
    summary = "🐾 **Daily Check: Have we fed John?**\n\n**Responses:**\n"
    
    for user_id, data in daily_responses[date_str].items():
        summary += f"• {data['name']}: {data['response']}\n"
    
    # Update the message with current responses
    try:
        await query.edit_message_text(
            text=summary,
            reply_markup=query.message.reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error updating message: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Feed Reminder Bot is active!\n\n"
        "I'll send a daily reminder at 6 PM (Singapore time) to check if John has been fed.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/test - Send a test reminder now\n"
        "/status - Show today's responses"
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger a reminder for testing"""
    await send_daily_question(context)
    await update.message.reply_text("Test reminder sent!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current day's responses"""
    from datetime import date
    today = str(date.today())
    
    if today not in daily_responses or not daily_responses[today]:
        await update.message.reply_text("No responses recorded for today yet.")
        return
    
    summary = "📊 **Today's Responses:**\n\n"
    for user_id, data in daily_responses[today].items():
        summary += f"• {data['name']}: {data['response']}\n"
    
    await update.message.reply_text(summary, parse_mode='Markdown')

async def post_init(application: Application) -> None:
    """Set up the job queue after application initialization"""
    # Schedule daily reminder at 6 PM Singapore time
    application.job_queue.run_daily(
        send_daily_question,
        time=time(hour=18, minute=0, tzinfo=TIMEZONE),
        name="daily_feed_reminder"
    )
    logging.info("Daily reminder scheduled for 6 PM Singapore time")

def main():
    """Start the bot"""
    # Create application with explicit job queue
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logging.info("Bot is starting with Singapore timezone...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()