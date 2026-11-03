package com.sec.android.app.uwbtest;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.UserHandle;
import android.util.Log;
import android.uwb.UwbManager;

/* JADX INFO: loaded from: classes.dex */
public class UwbCsTest extends Activity {
    private Context mContext;
    private UwbManager mUwbManager;
    String TAG = "UwbCsTest";
    private String cmd_uwb = "AT+UWBDTEST=";
    private String cmd_rfLoopBack = "0,0,9,5";
    BroadcastReceiver mUwbFactoryBroadcastReceiver = new BroadcastReceiver() { // from class: com.sec.android.app.uwbtest.UwbCsTest.1
        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            if (intent.getAction() == "com.samsung.android.uwb.test.action.RESPONSE") {
                String stringExtra = intent.getStringExtra("com.samsung.android.uwb.test.extra.DATA_STRING");
                Log.d(UwbCsTest.this.TAG, "onReceive in UI App result: " + stringExtra);
                if (stringExtra.contains("OK")) {
                    UwbCsTest.this.sendResult(true);
                } else {
                    UwbCsTest.this.sendResult(false);
                }
                Log.d(UwbCsTest.this.TAG, "Enable UWB after finishing Loopback test");
                UwbCsTest.this.mUwbManager.setUwbEnabled(true);
            }
        }
    };

    @Override // android.app.Activity
    public void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        this.mContext = this;
        this.mUwbManager = (UwbManager) getSystemService(UwbManager.class);
        registerReceiverAsUser(this.mUwbFactoryBroadcastReceiver, UserHandle.ALL, new IntentFilter("com.samsung.android.uwb.test.action.RESPONSE"), "com.samsung.permission.UWB_SYSTEM_PROTECTION", null, 2);
        startLoopback();
        try {
            Thread.sleep(150L);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override // android.app.Activity
    protected void onDestroy() {
        unregisterReceiver(this.mUwbFactoryBroadcastReceiver);
        super.onDestroy();
    }

    void sendBroadCast(String str, Bundle bundle) {
        Intent intent = new Intent();
        intent.setAction("com.samsung.android.uwb.test.action.REQUEST");
        intent.addFlags(268435456);
        String[] strArrSplit = str.split("=")[1].split(",");
        int i = Integer.parseInt(strArrSplit[0]);
        int[] iArr = {Integer.parseInt(strArrSplit[1]), Integer.parseInt(strArrSplit[2])};
        String str2 = strArrSplit[3];
        bundle.putInt("com.samsung.android.uwb.test.extra.ID", i);
        bundle.putIntArray("com.samsung.android.uwb.test.extra.DATA_INTEGER", iArr);
        bundle.putString("com.samsung.android.uwb.test.extra.DATA_STRING", str2);
        bundle.putString("com.samsung.android.uwb.test.extra.DATA_SENDER", this.mContext.getPackageName());
        intent.putExtras(bundle);
        sendBroadcast(intent, "com.samsung.permission.UWB_SYSTEM_PROTECTION");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResult(boolean z) {
        if (z) {
            Log.d(this.TAG, "--- sendResult success ");
            setResult(-1);
        } else {
            Log.d(this.TAG, "--- sendResult fail : Error occurred while UWB enable or RF loopback");
            setResult(2);
        }
        finish();
    }

    private void startLoopback() {
        String str = this.cmd_uwb + this.cmd_rfLoopBack;
        Log.d(this.TAG, "--- uwbRfLoopback is invoked");
        sendBroadCast(str, new Bundle());
    }
}
