package com.samsung.android.uwb_extension.factory;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.text.TextUtils;
import android.util.Log;
import com.android.internal.util.ArrayUtils;
import com.samsung.android.scpmlib_v1.BuildConfig;
import java.util.Arrays;

/* JADX INFO: loaded from: classes.dex */
public class UwbFactoryIntentManager {
    private static final String ACTION_UWB_TEST_REQUEST = "com.samsung.android.uwb.test.action.REQUEST";
    private static final String ACTION_UWB_TEST_RESPONSE = "com.samsung.android.uwb.test.action.RESPONSE";
    public static final String BOUND_LOCKED = "BL";
    public static final String BOUND_UNLOCKED = "BU";
    public static final String DATA_NG = "NG";
    public static final String DATA_NONE = "NONE";
    public static final String DATA_OK = "OK";
    private static final String EXTRA_DATA_INTEGER = "com.samsung.android.uwb.test.extra.DATA_INTEGER";
    private static final String EXTRA_DATA_SENDER = "com.samsung.android.uwb.test.extra.DATA_SENDER";
    private static final String EXTRA_DATA_STRING = "com.samsung.android.uwb.test.extra.DATA_STRING";
    private static final String EXTRA_ID = "com.samsung.android.uwb.test.extra.ID";
    private static final String EXTRA_LOOPBACK_COUNT = "com.samsung.android.uwb.test.extra.LOOPBACK_COUNT";
    private static final String EXTRA_LOOPBACK_INTERVAL = "com.samsung.android.uwb.test.extra.LOOPBACK_INTERVAL";
    private static final String FACTORY_AT_PACKAGE_NAME = "com.sec.facatfunction";
    public static final String FACTORY_CMD_SEPARATOR = "_";
    private static final String FACTORY_PACKAGE_NAME = "com.sec.factory";
    private static final String FACTORY_UI_PACKAGE_NAME = "com.sec.facuifunction";
    public static final String NG_BIND = "NG_BIND";
    public static final String NG_COUNT = "NG_COUNT";
    public static final String NOT_BOUND = "NB";
    public static final int POWER_INDEX_START = 6;
    private static final String TAG = UwbFactoryIntentManager.class.getSimpleName();
    public static final String UNKNOWN = "UN";
    private static final String UWBTEST_PACKAGE_NAME = "com.sec.android.app.uwbtest";
    private static final String UWB_SYSTEM_PROTECTION = "com.samsung.permission.UWB_SYSTEM_PROTECTION";
    private String mBroadcastSender = null;
    private final Context mContext;
    private final IUwbFactoryManager mIUwbFactoryManager;
    private final BroadcastReceiver mReceiver;
    private boolean mSentResult;
    private boolean mSkipRegulation;

    public UwbFactoryIntentManager(Context context, UwbFactoryManager uwbFactoryManager) {
        BroadcastReceiver broadcastReceiver = new BroadcastReceiver() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryIntentManager.1
            @Override // android.content.BroadcastReceiver
            public void onReceive(Context context2, Intent intent) {
                String data;
                String action = intent.getAction();
                if (!UwbFactoryIntentManager.ACTION_UWB_TEST_REQUEST.equals(action)) {
                    return;
                }
                int id = intent.getIntExtra(UwbFactoryIntentManager.EXTRA_ID, -1);
                int[] iData = intent.getIntArrayExtra(UwbFactoryIntentManager.EXTRA_DATA_INTEGER);
                String sData = intent.getStringExtra(UwbFactoryIntentManager.EXTRA_DATA_STRING);
                String sender = intent.getStringExtra(UwbFactoryIntentManager.EXTRA_DATA_SENDER);
                if (sender != null) {
                    UwbFactoryIntentManager.this.mBroadcastSender = sender;
                }
                if (ArrayUtils.isEmpty(iData)) {
                    Log.w(UwbFactoryIntentManager.TAG, "empty iData");
                    UwbFactoryIntentManager.this.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                }
                UwbFactoryIntentManager.this.showFactoryCommand(id, iData, sData);
                UwbFactoryIntentManager.this.mSentResult = false;
                if (!UwbFactoryIntentManager.this.mSkipRegulation) {
                    UwbFactoryIntentManager.this.mIUwbFactoryManager.sendMessage(31);
                    UwbFactoryIntentManager.this.mSkipRegulation = true;
                }
                String cmd = id + UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR + iData[0] + UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR + iData[1];
                if (iData.length == 3) {
                    data = Integer.toString(iData[2]);
                } else {
                    data = sData;
                }
                if (cmd.equals(UwbFactoryCommand.Group.UWB_0_3_0.getName()) && Integer.parseInt(data) == 4) {
                    int count = intent.getIntExtra(UwbFactoryIntentManager.EXTRA_LOOPBACK_COUNT, 0);
                    int interval = intent.getIntExtra(UwbFactoryIntentManager.EXTRA_LOOPBACK_INTERVAL, 0);
                    data = data + UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR + count + UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR + interval;
                }
                UwbFactoryCommand.TestCommand tc = UwbFactoryCommand.TestCommand.find(cmd, data);
                ParsedMessage msg = null;
                if (tc != null) {
                    msg = tc.process(data);
                } else {
                    Log.e(UwbFactoryIntentManager.TAG, "Not suported Command");
                }
                if (msg == null) {
                    Log.d(UwbFactoryIntentManager.TAG, "Invalid Test Case or Parameters");
                    UwbFactoryIntentManager.this.sendResponse(UwbFactoryIntentManager.DATA_NG);
                } else if (msg.getMsgId() != 400) {
                    UwbFactoryIntentManager.this.sendMessage(msg);
                } else {
                    Log.e(UwbFactoryIntentManager.TAG, "This message don'e need to send response");
                }
            }
        };
        this.mReceiver = broadcastReceiver;
        this.mContext = context;
        this.mIUwbFactoryManager = uwbFactoryManager;
        IntentFilter intentFilter = new IntentFilter(ACTION_UWB_TEST_REQUEST);
        context.registerReceiver(broadcastReceiver, intentFilter, "com.samsung.permission.UWB_SYSTEM_PROTECTION", null);
    }

    protected void finalize() throws Throwable {
        this.mContext.unregisterReceiver(this.mReceiver);
        super.finalize();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendMessage(ParsedMessage cmd) {
        switch (cmd.getType()) {
            case 0:
                this.mIUwbFactoryManager.sendMessage(cmd.getMsgId());
                break;
            case 1:
                this.mIUwbFactoryManager.sendMessage(cmd.getMsgId(), cmd.getObject());
                break;
            case 2:
                this.mIUwbFactoryManager.sendMessage(cmd.getMsgId(), cmd.getArg1(), cmd.getArg2());
                break;
            case 3:
                this.mIUwbFactoryManager.sendMessage(cmd.getMsgId(), cmd.getObject(), cmd.getArg1(), cmd.getArg2());
                break;
        }
    }

    public void sendResponse(int id, String sData) {
        sendResponse(id, sData, null);
    }

    public void sendResponse(String sData) {
        sendResponse(0, sData, null);
    }

    public void sendResponse(int id, String sData, int[] iData) {
        if (this.mSentResult) {
            return;
        }
        this.mSentResult = true;
        Log.d(TAG, "response ID: " + id + ", sData: " + sData + ", iData: " + (iData != null ? Arrays.toString(iData) : BuildConfig.FLAVOR));
        Intent intent = new Intent(ACTION_UWB_TEST_RESPONSE);
        intent.putExtra(EXTRA_ID, id);
        if (!TextUtils.isEmpty(sData)) {
            intent.putExtra(EXTRA_DATA_STRING, sData);
        }
        if (iData != null) {
            intent.putExtra(EXTRA_DATA_INTEGER, iData);
        }
        intent.setPackage(FACTORY_AT_PACKAGE_NAME);
        this.mContext.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
        intent.setPackage(FACTORY_UI_PACKAGE_NAME);
        this.mContext.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
        intent.setPackage(UWBTEST_PACKAGE_NAME);
        this.mContext.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
        String str = this.mBroadcastSender;
        if (str != null) {
            intent.setPackage(str);
            this.mContext.sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
            this.mBroadcastSender = null;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showFactoryCommand(int id, int[] iData, String sData) {
        StringBuffer sb = new StringBuffer("AT+UWBDTEST=" + id);
        for (int iDatum : iData) {
            sb.append("," + iDatum);
        }
        if (sData != null) {
            sb.append("," + sData);
        }
        Log.d(TAG, sb.toString());
    }

    private boolean isEmpty(String sData) {
        if (TextUtils.isEmpty(sData)) {
            Log.w(TAG, "empty sData");
            sendResponse(DATA_NG);
            return true;
        }
        return false;
    }
}
