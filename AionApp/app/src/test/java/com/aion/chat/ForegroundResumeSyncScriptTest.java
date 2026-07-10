package com.aion.chat;

import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class ForegroundResumeSyncScriptTest {
    @Test
    public void resumeScriptReconnectsWhenNeededAndAlwaysRefreshesMessages() {
        String script = ForegroundResumeSyncScript.build();

        assertTrue(script.contains("ws.readyState!==1"));
        assertTrue(script.contains("connectWS()"));
        assertTrue(script.contains("refreshCurrentConversationFromServer"));
        assertTrue(script.contains("refreshCurrentChatroomFromServer"));
        assertTrue(script.contains("querySelectorAll('iframe')"));
        assertFalse(script.contains("loadMessages"));

        int wsCheckIndex = script.indexOf("ws.readyState!==1");
        int refreshIndex = script.indexOf("refreshCurrentConversationFromServer");
        assertTrue(refreshIndex > wsCheckIndex);
    }
}
