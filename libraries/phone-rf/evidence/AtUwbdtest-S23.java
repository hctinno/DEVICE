package com.sec.facatfunction.aporiented.athandler;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import com.sec.facatfunction.aporiented.ResponseWriter;
import com.sec.facatfunction.support.FtUtil;
import egis.client.api.EgisFingerprint;

/* JADX INFO: loaded from: classes.dex */
public class AtUwbdtest extends AtCommandHandler {
    public static final String EXTRA_DATA_INTEGER = "com.samsung.android.uwb.test.extra.DATA_INTEGER";
    public static final String EXTRA_DATA_STRING = "com.samsung.android.uwb.test.extra.DATA_STRING";
    public static final String EXTRA_ID = "com.samsung.android.uwb.test.extra.ID";
    public static final String UWB_FACTORY_TEST = "com.samsung.android.uwb.test.action.REQUEST";
    public static final String UWB_FACTORY_TEST_RESULT = "com.samsung.android.uwb.test.action.RESPONSE";
    public static final String UWB_PERMISSION_NAME = "com.samsung.permission.UWB_SYSTEM_PROTECTION";
    public BroadcastReceiver mReceiver;

    public AtUwbdtest(Context context, ResponseWriter writer) {
        super(context);
        this.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtUwbdtest.1
            @Override // android.content.BroadcastReceiver
            public void onReceive(Context context2, Intent intent) {
                String action = intent.getAction();
                if (AtUwbdtest.UWB_FACTORY_TEST_RESULT.equals(action)) {
                    AtUwbdtest.this.stopReceiver();
                    String resData = intent.getStringExtra(AtUwbdtest.EXTRA_DATA_STRING);
                    if (resData == null) {
                        resData = intent.getStringExtra(AtUwbdtest.EXTRA_DATA_INTEGER);
                    }
                    int resCmd = intent.getIntExtra(AtUwbdtest.EXTRA_ID, 0);
                    FtUtil.log_d(AtUwbdtest.this.CLASS_NAME, "onReceive", "resCmd: " + resCmd);
                    AtUwbdtest.this.writer.write(AtUwbdtest.this.responseString(String.format("%d", Integer.valueOf(resCmd)), resData));
                }
            }
        };
        this.CMD_NAME = "UWBDTEST";
        this.CLASS_NAME = "AtUwbdtest";
        this.NUM_ARGS = 4;
        this.writer = writer;
    }

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public void startReceiver() {
        IntentFilter filter = new IntentFilter();
        filter.addAction(UWB_FACTORY_TEST_RESULT);
        this.context.registerReceiver(this.mReceiver, filter, UWB_PERMISSION_NAME, null);
    }

    public void stopReceiver() {
        this.context.unregisterReceiver(this.mReceiver);
    }

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public synchronized String handleCommand(String[] argu) {
        String resData = null;
        if (argu.length != (STAGE_PARALLEL ? this.NUM_ARGS + 1 : this.NUM_ARGS)) {
            return responseNA();
        }
        if (checkArgu(argu, new String[]{"0", "0", "0"})) {
            startReceiver();
            if (argu[3] != null) {
                if ("0".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 0);
                } else if (EgisFingerprint.MAJOR_VERSION.equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 1);
                } else if ("2".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 2);
                } else if (egis.optical.client.api.EgisFingerprint.MAJOR_VERSION.equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 3);
                } else if ("5".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 5);
                } else if ("6".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 6);
                } else if ("7".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 7);
                } else if ("9".equals(argu[3])) {
                    sendUwbTestCommand(0, 0, 0, 9);
                } else {
                    sendUwbTestCommand(0, 0, 0, argu[3]);
                }
            }
        } else if (checkArgu(argu, new String[]{"0", "0", EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 1, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "2"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 2, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 3, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "4"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 4, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "5"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 5, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "6"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 6, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "7"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 7, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "8"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 8, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "0", "9"})) {
            startReceiver();
            sendUwbTestCommand(0, 0, 9, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 1, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, "2", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 2, 0);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, egis.optical.client.api.EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 3, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, "4", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 4, 0);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, "5"})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 5, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", EgisFingerprint.MAJOR_VERSION, "6"})) {
            startReceiver();
            sendUwbTestCommand(0, 1, 6, 0);
        } else if (checkArgu(argu, new String[]{"0", "2", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 0, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "2", EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 1, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "2", "2"})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 2, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "2", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 3, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "2", "4"})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 4, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "2", "5", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 2, 5, 0);
        } else if (checkArgu(argu, new String[]{"0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION, "0", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 3, 0, 0);
        } else if (checkArgu(argu, new String[]{"0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION, "0", EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 3, 0, 1);
        } else if (checkArgu(argu, new String[]{"0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION, "0", "2"})) {
            startReceiver();
            sendUwbTestCommand(0, 3, 0, 2);
        } else if (checkArgu(argu, new String[]{"0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION, "0", egis.optical.client.api.EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 3, 0, 3);
        } else if (checkArgu(argu, new String[]{"0", "4", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 4, 0, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "4", EgisFingerprint.MAJOR_VERSION})) {
            startReceiver();
            sendUwbTestCommand(0, 4, 1, argu[3]);
        } else if (checkArgu(argu, new String[]{"0", "6", "0"})) {
            startReceiver();
            sendUwbTestCommand(0, 6, 0, argu[3]);
        } else if (checkArgu(argu, new String[]{EgisFingerprint.MAJOR_VERSION, "0", "0", "0"})) {
            startReceiver();
            sendUwbTestCommand(1, 0, 0, 0);
        } else {
            resData = responseNA();
        }
        return resData;
    }

    private void sendUwbTestCommand(int cmd_id, int i_data2, int i_data3, int i_data4) {
        int[] i_data = {i_data2, i_data3, i_data4};
        Intent intent = new Intent(UWB_FACTORY_TEST);
        intent.putExtra(EXTRA_ID, cmd_id);
        intent.putExtra(EXTRA_DATA_INTEGER, i_data);
        this.context.sendBroadcast(intent, UWB_PERMISSION_NAME);
    }

    private void sendUwbTestCommand(int cmd_id, int i_data2, int i_data3, String s_data) {
        int[] i_data = {i_data2, i_data3};
        Intent intent = new Intent(UWB_FACTORY_TEST);
        intent.putExtra(EXTRA_ID, cmd_id);
        intent.putExtra(EXTRA_DATA_INTEGER, i_data);
        intent.putExtra(EXTRA_DATA_STRING, s_data);
        this.context.sendBroadcast(intent, UWB_PERMISSION_NAME);
    }
}
