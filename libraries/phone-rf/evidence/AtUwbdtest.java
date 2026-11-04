package com.sec.facatfunction.aporiented.athandler;

import android.content.Intent;
import android.content.IntentFilter;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtUwbdtest extends AtCommandHandler {
    public AnonymousClass1 mReceiver;

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public final synchronized String handleCommand(String[] strArr) {
        String str;
        try {
            if (strArr.length != this.NUM_ARGS) {
                AtCommandHandler.responseNA();
                return "\r\n+CME Error:NA\r\n\r\nOK\r\n";
            }
            if (checkArgu(strArr, new String[]{"0", "0", "0"})) {
                startReceiver();
                String str2 = strArr[3];
                if (str2 != null) {
                    if ("0".equals(str2)) {
                        sendUwbTestCommand(0, 0, 0, 0);
                    } else if ("1".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 1);
                    } else if ("2".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 2);
                    } else if ("3".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 3);
                    } else if ("5".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 5);
                    } else if ("6".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 6);
                    } else if ("7".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 7);
                    } else if ("9".equals(strArr[3])) {
                        sendUwbTestCommand(0, 0, 0, 9);
                    } else {
                        sendUwbTestCommand(0, 0, 0, strArr[3]);
                    }
                }
            } else if (checkArgu(strArr, new String[]{"0", "0", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 1, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "2"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 2, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "3"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 3, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "4"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 4, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "5"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 5, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "6"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 6, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "7"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 7, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "8"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 8, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "0", "9"})) {
                startReceiver();
                sendUwbTestCommand(0, 0, 9, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "1", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 1, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "1", "2", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 2, 0);
            } else if (checkArgu(strArr, new String[]{"0", "1", "3"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 3, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "1", "4", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 4, 0);
            } else if (checkArgu(strArr, new String[]{"0", "1", "4", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 4, 1);
            } else if (checkArgu(strArr, new String[]{"0", "1", "5"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 5, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "1", "6"})) {
                startReceiver();
                sendUwbTestCommand(0, 1, 6, 0);
            } else if (checkArgu(strArr, new String[]{"0", "2", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 0, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "2", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 1, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "2", "2"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 2, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "2", "3"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 3, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "2", "4"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 4, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "2", "5", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 2, 5, 0);
            } else if (checkArgu(strArr, new String[]{"0", "3", "0", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 3, 0, 0);
            } else if (checkArgu(strArr, new String[]{"0", "3", "0", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 3, 0, 1);
            } else if (checkArgu(strArr, new String[]{"0", "3", "0", "2"})) {
                startReceiver();
                sendUwbTestCommand(0, 3, 0, 2);
            } else if (checkArgu(strArr, new String[]{"0", "3", "0", "3"})) {
                startReceiver();
                sendUwbTestCommand(0, 3, 0, 3);
            } else if (checkArgu(strArr, new String[]{"0", "4", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 4, 0, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "4", "1"})) {
                startReceiver();
                sendUwbTestCommand(0, 4, 1, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "6", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 6, 0, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"0", "7", "0"})) {
                startReceiver();
                sendUwbTestCommand(0, 7, 0, strArr[3]);
            } else if (checkArgu(strArr, new String[]{"1", "0", "0", "0"})) {
                startReceiver();
                sendUwbTestCommand(1, 0, 0, 0);
            } else if (checkArgu(strArr, new String[]{"3", "0", "0", "0"})) {
                startReceiver();
                sendUwbTestCommand(3, 0, 0, 0);
            } else if (checkArgu(strArr, new String[]{"3", "0", "0", "1"})) {
                startReceiver();
                sendUwbTestCommand(3, 0, 0, 1);
            } else {
                if (!checkArgu(strArr, new String[]{"3", "1", "0"})) {
                    if (checkArgu(strArr, new String[]{"3", "1", "1"})) {
                        startReceiver();
                        sendUwbTestCommand(3, 1, 1, strArr[3]);
                    } else {
                        AtCommandHandler.responseNA();
                        str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                    }
                    return str;
                }
                startReceiver();
                sendUwbTestCommand(3, 1, 0, strArr[3]);
            }
            str = null;
            return str;
        } catch (Throwable th) {
            throw th;
        }
    }

    public final void sendUwbTestCommand(int i, int i2, int i3, int i4) {
        int[] iArr = {i2, i3, i4};
        Intent intent = new Intent("com.samsung.android.uwb.test.action.REQUEST");
        intent.putExtra("com.samsung.android.uwb.test.extra.ID", i);
        intent.putExtra("com.samsung.android.uwb.test.extra.DATA_INTEGER", iArr);
        this.context.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
    }

    public final void startReceiver() {
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("com.samsung.android.uwb.test.action.RESPONSE");
        this.context.registerReceiver(this.mReceiver, intentFilter, "com.samsung.permission.UWB_SYSTEM_PROTECTION", null, 2);
    }

    public final void sendUwbTestCommand(int i, int i2, int i3, String str) {
        int[] iArr = {i2, i3};
        Intent intent = new Intent("com.samsung.android.uwb.test.action.REQUEST");
        intent.putExtra("com.samsung.android.uwb.test.extra.ID", i);
        intent.putExtra("com.samsung.android.uwb.test.extra.DATA_INTEGER", iArr);
        intent.putExtra("com.samsung.android.uwb.test.extra.DATA_STRING", str);
        this.context.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
    }
}
