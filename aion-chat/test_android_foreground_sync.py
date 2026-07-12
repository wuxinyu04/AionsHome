import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


class AndroidForegroundSyncTest(unittest.TestCase):
    def test_android_resume_uses_foreground_sync_helper(self):
        activity = read_text("AionApp/app/src/main/java/com/aion/chat/WebViewActivity.java")

        self.assertIn("ForegroundResumeSyncScript.build()", activity)
        self.assertNotIn("loadMessages", activity)

    def test_android_page_load_completion_runs_foreground_sync(self):
        activity = read_text("AionApp/app/src/main/java/com/aion/chat/WebViewActivity.java")
        on_finished = activity.split("public void onPageFinished", 1)[1].split(
            "public void onReceivedError", 1
        )[0]

        self.assertIn("runForegroundResumeSync();", on_finished)

    def test_chat_page_exposes_current_conversation_refresh(self):
        chat_js = read_text("aion-chat/static/chat.js")

        self.assertIn("async function refreshCurrentConversationFromServer", chat_js)
        self.assertIn("window.refreshCurrentConversationFromServer", chat_js)
        self.assertIn("`/api/conversations/${currentConvId}/messages?limit=${MSG_PAGE_SIZE}`", chat_js)

    def test_chatroom_page_exposes_current_room_refresh(self):
        chatroom_js = read_text("aion-chat/static/chatroom.js")

        self.assertIn("async function refreshCurrentChatroomFromServer", chatroom_js)
        self.assertIn("window.refreshCurrentChatroomFromServer", chatroom_js)
        self.assertIn("`/rooms/${roomId}/messages?limit=100`", chatroom_js)

    def test_foreground_script_refreshes_embedded_chatroom_frames(self):
        script = read_text("AionApp/app/src/main/java/com/aion/chat/ForegroundResumeSyncScript.java")

        self.assertIn("refreshCurrentChatroomFromServer", script)
        self.assertIn("querySelectorAll('iframe')", script)


if __name__ == "__main__":
    unittest.main()
