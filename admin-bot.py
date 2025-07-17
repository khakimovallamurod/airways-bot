from telegram.ext import (
    CommandHandler, MessageHandler, filters, 
    ConversationHandler, Application, CallbackQueryHandler
)
from telegram import Update
from config import get_token
import handlears
import asyncio

async def start_jobs(dp):
    job_queue = dp.job_queue
    await job_queue.start()

    await handlears.restart_active_signals(dp)

def main():
    TOKEN = get_token()

    dp = Application.builder().token(TOKEN).build()

    dp.add_handler(CommandHandler('start', handlears.start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("airwaystart", handlears.railway_start)],
        states={
            handlears.FROM_CITY: [CallbackQueryHandler(handlears.from_city_selected)],
            handlears.TO_CITY: [CallbackQueryHandler(handlears.to_city_selected)],
            handlears.DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.select_class)],
            handlears.SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.signal_start)],
            handlears.ADD_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.add_comment_signal)],
       
        },
        fallbacks=[
            CommandHandler("cancel", handlears.cancel),
            ],
        per_message=False
    )

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler('addadmin', handlears.admin_start)],
        states={
            handlears.ID_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.insert_admin)]
        },
        fallbacks=[CommandHandler("cancel", handlears.cancel)],
        per_message=False
    )

    dp.add_handler(conv_handler)
    dp.add_handler(admin_handler)
    dp.add_handler(CommandHandler('viewactives', handlears.view_actives))
    dp.add_handler(CallbackQueryHandler(handlears.stop_signal, pattern="stop_signal"))

    asyncio.get_event_loop().run_until_complete(start_jobs(dp))

    dp.run_polling(allowed_updates=Update.ALL_TYPES, timeout=30)

if __name__ == '__main__':
    main()
