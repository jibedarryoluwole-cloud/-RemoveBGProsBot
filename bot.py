import os
import logging
import io
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp
from PIL import Image
import rembg

# ===== CONFIGURATION =====
TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
REMOVEBG_API_KEY = os.environ.get("REMOVEBG_API_KEY")  # Optional: for remove.bg API

# ===== LOGGING SETUP =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== TOKEN VALIDATION =====
if not TOKEN:
    logger.error("❌ NO TOKEN FOUND! Please set TELEGRAM_TOKEN environment variable.")
    exit(1)

logger.info(f"✅ Token loaded successfully! First 10 chars: {TOKEN[:10]}...")
logger.info(f"✅ Remove.bg API: {'✅ Set' if REMOVEBG_API_KEY else '❌ Not set'}")

# ===== BACKGROUND REMOVAL FUNCTIONS =====

async def remove_background_rembg(image_data):
    """
    Remove background using rembg library (free, runs locally)
    Based on existing Telegram bot implementations using rembg [citation:3][citation:5]
    """
    try:
        # Open image
        input_image = Image.open(io.BytesIO(image_data))
        
        # Remove background using rembg
        output_image = rembg.remove(input_image)
        
        # Save to bytes
        output = io.BytesIO()
        output_image.save(output, format='PNG')
        output.seek(0)
        
        return output
    except Exception as e:
        logger.error(f"rembg error: {str(e)}")
        return None

async def remove_background_removebg_api(image_data):
    """
    Remove background using remove.bg API
    Requires REMOVEBG_API_KEY environment variable [citation:2]
    """
    if not REMOVEBG_API_KEY:
        return None
    
    try:
        url = "https://api.remove.bg/v1.0/removebg"
        headers = {
            "X-Api-Key": REMOVEBG_API_KEY
        }
        
        # Prepare the image
        files = {
            "image_file": image_data
        }
        
        data = {
            "size": "auto",
            "format": "png"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, files=files, data=data) as response:
                if response.status == 200:
                    result = await response.read()
                    output = io.BytesIO(result)
                    output.seek(0)
                    return output
                else:
                    error_text = await response.text()
                    logger.error(f"remove.bg API error: {response.status} - {error_text}")
                    return None
    except Exception as e:
        logger.error(f"remove.bg API error: {str(e)}")
        return None

async def remove_background(image_data):
    """
    Remove background using available method
    Try remove.bg API first if key is set, otherwise fallback to rembg
    """
    # Try remove.bg API first if key is set
    if REMOVEBG_API_KEY:
        result = await remove_background_removebg_api(image_data)
        if result:
            return result, "remove.bg API"
    
    # Fallback to rembg (free)
    result = await remove_background_rembg(image_data)
    if result:
        return result, "rembg (local)"
    
    return None, None

# ===== BOT COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome = (
        "🖼️ *Welcome to RemoveBG Pros Bot!*\n\n"
        "I remove backgrounds from images instantly!\n\n"
        "📝 *What I can do:*\n"
        "• Remove backgrounds from photos\n"
        "• Return PNG with transparent background\n"
        "• Preserve original image quality\n"
        "• Works on any device\n\n"
        "🔧 *Commands:*\n"
        "/start - Show this message\n"
        "/help - Get help\n"
        "/about - About this bot\n"
        "/stats - Your usage statistics\n\n"
        "💡 *How to use:*\n"
        "1. Send me an image (photo or document)\n"
        "2. I'll remove the background\n"
        "3. Get your result instantly!\n\n"
        "⚡ *Pro Tip:* Send as a document for best quality"
    )
    
    keyboard = [
        [InlineKeyboardButton("🖼️ Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = (
        "🤖 *Help Center*\n\n"
        "📝 *How to use this bot:*\n\n"
        "1️⃣ *Send an image:*\n"
        "Send any photo or image to the bot\n\n"
        "2️⃣ *Choose method:*\n"
        "• Send as photo - Quick processing\n"
        "• Send as document - Better quality\n\n"
        "3️⃣ *Get results:*\n"
        "The bot will process and send back a PNG with transparent background\n\n"
        "🔧 *Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/about - About this bot\n"
        "/stats - Your usage statistics\n\n"
        "⚡ *Tips:*\n"
        "• Images with clear subjects work best\n"
        "• Send as document for best quality\n"
        "• The bot keeps your images private"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send about information"""
    about_text = (
        "📱 *About RemoveBG Pros Bot*\n\n"
        "🤖 *Name:* RemoveBG Pros Bot\n"
        "📝 *Username:* @RemoveBGProsBot\n"
        "🔧 *Version:* 1.0.0\n"
        "🛠 *Built with:* python-telegram-bot, rembg\n"
        "🎯 *Purpose:* Remove backgrounds from images\n\n"
        "📚 *Source Code:* Available on GitHub\n"
        "💻 *Deployed on:* Railway"
    )
    await update.message.reply_text(about_text, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    processed = context.user_data.get("processed_count", 0)
    
    stats_text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 *User ID:* {user_id}\n"
        f"🖼️ *Images Processed:* {processed}\n"
        f"⚡ *Status:* Active\n\n"
        f"Keep sending images to remove backgrounds!"
    )
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images sent to the bot"""
    processing_msg = await update.message.reply_text(
        "🔄 *Removing background...*\n⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    try:
        # Get the image file
        if update.message.photo:
            # Photo upload (compressed)
            photo_file = await update.message.photo[-1].get_file()
            image_data = await photo_file.download_as_bytearray()
            file_type = "photo"
        elif update.message.document:
            # Document upload (higher quality)
            document = update.message.document
            if document.mime_type and document.mime_type.startswith('image/'):
                doc_file = await document.get_file()
                image_data = await doc_file.download_as_bytearray()
                file_type = "document"
            else:
                await processing_msg.delete()
                await update.message.reply_text(
                    "❌ Please send an image file (JPG, PNG, etc.)"
                )
                return
        else:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ Please send an image to remove background."
            )
            return
        
        # Remove background
        result, method = await remove_background(image_data)
        
        if result:
            # Update user stats
            context.user_data["processed_count"] = context.user_data.get("processed_count", 0) + 1
            
            await processing_msg.delete()
            
            # Send the processed image
            await update.message.reply_document(
                result,
                filename="no-bg.png",
                caption=f"✅ *Background Removed!*\n\n"
                        f"🤖 *Method:* {method}\n"
                        f"📦 *File Type:* {file_type.upper()}\n\n"
                        f"🖼️ *Image saved as PNG with transparent background*",
                parse_mode="Markdown"
            )
        else:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ *Failed to remove background*\n\n"
                "Please try again with a different image.\n\n"
                "💡 Tips:\n"
                "• Try an image with a clear subject\n"
                "• Make sure the image is not too large\n"
                "• Try sending as a document for better quality",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Image processing error: {str(e)}")
        await processing_msg.delete()
        await update.message.reply_text(
            f"❌ *Error processing image*\n\n"
            f"{str(e)}\n\n"
            f"Please try again.",
            parse_mode="Markdown"
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        help_text = (
            "🤖 *How to use this bot:*\n\n"
            "1. Send an image\n"
            "2. The bot removes the background\n"
            "3. Get a PNG with transparent background!\n\n"
            "Send as document for best quality."
        )
        await query.edit_message_text(help_text, parse_mode="Markdown")
    
    elif query.data == "remove_bg":
        await query.edit_message_text(
            "📸 *Ready to remove background!*\n\n"
            "Please send me an image (photo or document).\n\n"
            "💡 For best quality, send as a document.",
            parse_mode="Markdown"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ===== MAIN APPLICATION =====
def main():
    """Start the bot"""
    logger.info("🚀 Starting RemoveBG Pros Bot...")
    logger.info(f"🤖 Bot Username: @RemoveBGProsBot")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handlers for images
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image))
    
    # Add callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot is ready! Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
