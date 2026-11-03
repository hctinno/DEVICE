package com.sec.facatfunction.aporiented.athandler;

import android.content.BroadcastReceiver;
import android.content.Context;
import androidx.profileinstaller.ProfileTranscoder$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.AtCommandInfo;
import com.sec.facatfunction.aporiented.ResponseWriter;
import com.sec.facatfunction.support.FtUtil;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public abstract class AtCommandHandler {
    public Context context;
    public String CMD_NAME = "CMD_NAME";
    public String CLASS_NAME = "AtCommandHandler";
    public int NUM_ARGS = 0;
    public ResponseWriter writer = null;

    public AtCommandHandler(Context context) {
        this.context = context;
    }

    public static void responseNA() {
        AtCommandInfo.getInstance().addCommandHistory("\r\n+CME Error:NA\r\n\r\nOK\r\n");
    }

    public final boolean checkArgu(String[] strArr, String[] strArr2) {
        for (int i = 0; i < strArr2.length; i++) {
            try {
                if (!strArr[i].equalsIgnoreCase(strArr2[i])) {
                    return false;
                }
            } catch (ArrayIndexOutOfBoundsException unused) {
                FtUtil.log_i(this.CLASS_NAME, "checkArgu", "ArrayIndexOutOfBoundsException");
                return false;
            }
        }
        return true;
    }

    public abstract String handleCommand(String[] strArr);

    public final String responseNG(String str) {
        String str2 = "\r\n+" + this.CMD_NAME + ":" + str + ",NG\r\n\r\nOK\r\n";
        AtCommandInfo.getInstance().addCommandHistory(str2);
        AtCommandInfo.getInstance();
        AtCommandInfo.setFailInfo(this.CMD_NAME, "Unknown");
        return str2;
    }

    public final String responseOK(String str) {
        String str2 = "\r\n+" + this.CMD_NAME + ":" + str + ",OK\r\n\r\nOK\r\n";
        AtCommandInfo.getInstance().addCommandHistory(str2);
        return str2;
    }

    public final String responseString(String str) {
        String str2 = "\r\n+" + this.CMD_NAME + ":" + str + "\r\n\r\nOK\r\n";
        AtCommandInfo.getInstance().addCommandHistory(str2);
        return str2;
    }

    public final void stopReceiver(BroadcastReceiver broadcastReceiver) {
        FtUtil.log_i(this.CLASS_NAME, "stopReceiver");
        if (broadcastReceiver != null) {
            try {
                this.context.unregisterReceiver(broadcastReceiver);
            } catch (IllegalArgumentException e) {
                FtUtil.log_e(e);
                FtUtil.log_e(this.CLASS_NAME, "stopReceiver", "Can not unregisterReceiver");
            }
        }
    }

    public final String responseString(String str, String str2) {
        StringBuilder sb = new StringBuilder("\r\n+");
        sb.append(this.CMD_NAME);
        sb.append(":");
        sb.append(str);
        sb.append(",");
        String strM = ProfileTranscoder$$ExternalSyntheticOutline0.m(sb, str2, "\r\n\r\nOK\r\n");
        AtCommandInfo.getInstance().addCommandHistory(strM);
        if (strM.contains("NG") && this.CMD_NAME != "HWPARAMD") {
            AtCommandInfo.getInstance();
            AtCommandInfo.setFailInfo(this.CMD_NAME, str2);
        }
        return strM;
    }
}
