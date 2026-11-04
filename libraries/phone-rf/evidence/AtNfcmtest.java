package com.sec.facatfunction.aporiented.athandler;

import android.app.ActivityManager;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.nfc.NfcAdapter;
import android.os.Binder;
import android.os.Handler;
import android.os.Message;
import com.samsung.android.nfc.adapter.SamsungNfcAdapter;
import com.sec.facatfunction.aporiented.DigitizerElectricService$1$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.ResponseWriter;
import com.sec.facatfunction.support.FtUtil;
import com.sec.factorymodule.modules.ModuleDevice;
import com.sec.factorymodule.modules.ModuleNfc;
import com.sec.xmldata.support.NVAccessor;
import com.sec.xmldata.support.Support$Path;
import java.io.File;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtNfcmtest extends AtCommandHandler {
    public static final byte[] FILE_ID_PROP1 = {-31, 5};
    public static final byte[] FILE_ID_PROP2 = {-31, 6};
    public static final byte[] FILE_ID_PROP3 = {-31, 7};
    public static final byte[] FILE_ID_PROP4 = {-31, 8};
    public boolean mEndReceiver;
    public final NfcAdapter mNfcAdapter;
    public AnonymousClass2 mNfcTestHandler;
    public final AnonymousClass1 mReceiver;
    public final SamsungNfcAdapter mSamsungNfcAdapter;

    /* JADX WARN: Failed to restore enum class, 'enum' modifier and super class removed */
    /* JADX WARN: Unknown enum class pattern. Please report as an issue! */
    /* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
    final class NfcStatus {
        public static final /* synthetic */ NfcStatus[] $VALUES;
        public static final NfcStatus ENABLED;
        public static final NfcStatus NONE;
        public static final NfcStatus OFF;
        public static final NfcStatus ON;

        static {
            NfcStatus nfcStatus = new NfcStatus("NONE", 0);
            NONE = nfcStatus;
            NfcStatus nfcStatus2 = new NfcStatus("ENABLED", 1);
            ENABLED = nfcStatus2;
            NfcStatus nfcStatus3 = new NfcStatus("ON", 2);
            ON = nfcStatus3;
            NfcStatus nfcStatus4 = new NfcStatus("OFF", 3);
            OFF = nfcStatus4;
            $VALUES = new NfcStatus[]{nfcStatus, nfcStatus2, nfcStatus3, nfcStatus4, new NfcStatus("DISABLED", 4)};
        }

        public static NfcStatus valueOf(String str) {
            return (NfcStatus) Enum.valueOf(NfcStatus.class, str);
        }

        public static NfcStatus[] values() {
            return (NfcStatus[]) $VALUES.clone();
        }
    }

    /* JADX WARN: Type inference failed for: r0v1, types: [com.sec.facatfunction.aporiented.athandler.AtNfcmtest$1] */
    public AtNfcmtest(Context context, ResponseWriter responseWriter) {
        super(context);
        this.mEndReceiver = true;
        this.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtNfcmtest.1
            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                String action = intent.getAction();
                if ("com.sec.android.app.nfcntest.NFC_TEST_RESPONSE".equals(action) || "com.sec.android.app.nfctest.NFC_TEST_RESPONSE_V2".equals(action) || "com.sec.android.app.nfctest.NFC_TEST_RESPONSE_V3".equals(action)) {
                    FtUtil.log_d(AtNfcmtest.this.CLASS_NAME, "Receive ACTION_NFC_RESPONSE(V1/V2/V3)");
                    AtNfcmtest atNfcmtest = AtNfcmtest.this;
                    if (atNfcmtest.mEndReceiver) {
                        atNfcmtest.context.unregisterReceiver(atNfcmtest.mReceiver);
                    } else {
                        atNfcmtest.mEndReceiver = true;
                    }
                    String stringExtra = intent.getStringExtra("S_DATA");
                    if (stringExtra == null) {
                        stringExtra = intent.getStringExtra("I_DATA");
                    }
                    int intExtra = intent.getIntExtra("CMDID", 0);
                    DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra, "resCmd: ", AtNfcmtest.this.CLASS_NAME, "onReceive");
                    AtNfcmtest atNfcmtest2 = AtNfcmtest.this;
                    atNfcmtest2.writer.write(atNfcmtest2.responseString(String.format("%d", Integer.valueOf(intExtra)), stringExtra));
                    return;
                }
                if ("com.samsung.android.nfc.test.action.RESPONSE".equals(action)) {
                    int intExtra2 = intent.getIntExtra("com.samsung.android.nfc.test.extra.ID", -1);
                    switch (intExtra2) {
                        case 21:
                        case 22:
                        case 23:
                            FtUtil.log_d(AtNfcmtest.this.CLASS_NAME, "Receive ACTION_NFC_RESPONSE(V1/V2/V3)");
                            AtNfcmtest atNfcmtest3 = AtNfcmtest.this;
                            if (atNfcmtest3.mEndReceiver) {
                                atNfcmtest3.context.unregisterReceiver(atNfcmtest3.mReceiver);
                            } else {
                                atNfcmtest3.mEndReceiver = true;
                            }
                            String stringExtra2 = intent.getStringExtra("com.samsung.android.nfc.test.extra.DATA_STRING");
                            if (stringExtra2 == null) {
                                stringExtra2 = intent.getStringExtra("com.samsung.android.nfc.test.extra.DATA_INTEGER");
                            }
                            int intExtra3 = intent.getIntExtra("com.samsung.android.nfc.test.extra.CMD", 0);
                            DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra3, "resCmd: ", AtNfcmtest.this.CLASS_NAME, "onReceive");
                            AtNfcmtest atNfcmtest4 = AtNfcmtest.this;
                            atNfcmtest4.writer.write(atNfcmtest4.responseString(String.format("%d", Integer.valueOf(intExtra3)), stringExtra2));
                            break;
                        default:
                            FtUtil.log_e(AtNfcmtest.this.CLASS_NAME, "Unknown ID: " + intExtra2);
                            break;
                    }
                    return;
                }
                if (!"com.samsung.android.ese.test.action.RESPONSE".equals(action)) {
                    if ("com.samsung.android.nfc.action.STOP_APC_RESP".equals(action)) {
                        FtUtil.log_d(AtNfcmtest.this.CLASS_NAME, "Receive ACTION_NFC_STOP_APC_RESP");
                        AtNfcmtest atNfcmtest5 = AtNfcmtest.this;
                        if (atNfcmtest5.mEndReceiver) {
                            atNfcmtest5.context.unregisterReceiver(atNfcmtest5.mReceiver);
                        } else {
                            atNfcmtest5.mEndReceiver = true;
                        }
                        String stringExtra3 = intent.getStringExtra("DATA");
                        int intExtra4 = intent.getIntExtra("ATTR", 0);
                        DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra4, "resCmd: ", AtNfcmtest.this.CLASS_NAME, "onReceive");
                        AtNfcmtest atNfcmtest6 = AtNfcmtest.this;
                        atNfcmtest6.writer.write(atNfcmtest6.responseString(String.format("%d", Integer.valueOf(intExtra4)), stringExtra3));
                        return;
                    }
                    return;
                }
                int intExtra5 = intent.getIntExtra("com.samsung.android.ese.test.extra.ID", -1);
                if (intExtra5 != 21) {
                    FtUtil.log_e(AtNfcmtest.this.CLASS_NAME, "Unknown ID: " + intExtra5);
                    return;
                }
                FtUtil.log_d(AtNfcmtest.this.CLASS_NAME, "Receive ACTION_NFC_RESPONSE(V1)");
                AtNfcmtest atNfcmtest7 = AtNfcmtest.this;
                if (atNfcmtest7.mEndReceiver) {
                    atNfcmtest7.context.unregisterReceiver(atNfcmtest7.mReceiver);
                } else {
                    atNfcmtest7.mEndReceiver = true;
                }
                String stringExtra4 = intent.getStringExtra("com.samsung.android.ese.test.extra.DATA_STRING");
                if (stringExtra4 == null) {
                    stringExtra4 = intent.getStringExtra("com.samsung.android.ese.test.extra.DATA_INTEGER");
                }
                int intExtra6 = intent.getIntExtra("com.samsung.android.ese.test.extra.CMD", 0);
                DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra6, "resCmd: ", AtNfcmtest.this.CLASS_NAME, "onReceive");
                AtNfcmtest atNfcmtest8 = AtNfcmtest.this;
                atNfcmtest8.writer.write(atNfcmtest8.responseString(String.format("%d", Integer.valueOf(intExtra6)), stringExtra4));
            }
        };
        this.CMD_NAME = "NFCMTEST";
        this.CLASS_NAME = "AtNfcmtest";
        this.NUM_ARGS = 2;
        this.writer = responseWriter;
        this.mNfcAdapter = NfcAdapter.getDefaultAdapter(context);
        if (context.getPackageManager().hasSystemFeature("android.hardware.nfc")) {
            try {
                this.mSamsungNfcAdapter = SamsungNfcAdapter.getDefaultAdapter(context);
            } catch (NoClassDefFoundError unused) {
                FtUtil.log_d(this.CLASS_NAME, "getSamsungNfcAdapterInstance", "SamsungNfcAdapter is null due to be NoClassDefFoundError");
            }
        }
    }

    public static int bytesToInt(byte[] bArr) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bArr) {
            sb.append(String.format("%02X", Integer.valueOf(b & 255)));
        }
        return Integer.parseInt(sb.toString(), 16);
    }

    public final boolean checkNfcInitPropValue() {
        boolean zEqualsIgnoreCase = "true".equalsIgnoreCase(Support$Path.getProp("nfc.initialized"));
        int i = 0;
        while (!zEqualsIgnoreCase) {
            int i2 = i + 1;
            if (i > 15) {
                i = i2;
                break;
            }
            FtUtil.Sleep.sleep(1000L);
            boolean zEqualsIgnoreCase2 = "true".equalsIgnoreCase(Support$Path.getProp("nfc.initialized"));
            DigitizerElectricService$1$$ExternalSyntheticOutline0.m(i2, "Check nfc init count: ", this.CLASS_NAME, "checkNfcInitPropValue");
            i = i2;
            zEqualsIgnoreCase = zEqualsIgnoreCase2;
        }
        return i <= 15;
    }

    public final String getPackageName() {
        try {
            ActivityManager activityManager = (ActivityManager) this.context.getSystemService("activity");
            if (activityManager.getRunningAppProcesses() == null) {
                return "";
            }
            int callingPid = Binder.getCallingPid();
            for (ActivityManager.RunningAppProcessInfo runningAppProcessInfo : activityManager.getRunningAppProcesses()) {
                if (runningAppProcessInfo.pid == callingPid) {
                    return runningAppProcessInfo.processName;
                }
            }
            return "";
        } catch (Exception e) {
            FtUtil.log_d(this.CLASS_NAME, "Error occurs on checking package name.");
            e.printStackTrace();
            return "";
        }
    }

    public final String getT4tData(byte[] bArr) {
        if (!ModuleNfc.isSupportT4t(this.context)) {
            return "T4T_NOT_SUPPORTED";
        }
        Context context = this.context;
        int iBytesToInt = bytesToInt(bArr);
        byte[] bArr2 = null;
        NfcAdapter defaultAdapter = !context.getPackageManager().hasSystemFeature("android.hardware.nfc") ? null : NfcAdapter.getDefaultAdapter(context);
        if (defaultAdapter != null) {
            try {
                Class[] clsArr = new Class[0];
                Method declaredMethod = NfcAdapter.class.getDeclaredMethod("getNfcOemExtension", null);
                declaredMethod.setAccessible(true);
                Object objInvoke = declaredMethod.invoke(defaultAdapter, null);
                Class[] clsArr2 = new Class[0];
                Method declaredMethod2 = objInvoke.getClass().getDeclaredMethod("getT4tNdefNfcee", null);
                declaredMethod2.setAccessible(true);
                Object objInvoke2 = declaredMethod2.invoke(objInvoke, null);
                bArr2 = (byte[]) objInvoke2.getClass().getDeclaredMethod("readData", Integer.TYPE).invoke(objInvoke2, Integer.valueOf(iBytesToInt));
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        if (bArr2 == null) {
            FtUtil.log_d(this.CLASS_NAME, "getT4tData", "Nfc T4T read fail : T4T Data is null");
            return "NONE";
        }
        String str = new String(bArr2, StandardCharsets.UTF_8);
        FtUtil.log_d(this.CLASS_NAME, "getT4tData", "Nfc T4T read success : ".concat(str));
        return str;
    }

    /* JADX WARN: Multi-variable type inference failed */
    /* JADX WARN: Type inference failed for: r15v117 */
    /* JADX WARN: Type inference failed for: r15v118 */
    /* JADX WARN: Type inference failed for: r15v90 */
    /* JADX WARN: Type inference failed for: r15v96, types: [java.lang.String] */
    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public final synchronized String handleCommand(String[] strArr) {
        String strResponseString;
        if (strArr.length != this.NUM_ARGS) {
            AtCommandHandler.responseNA();
            return "\r\n+CME Error:NA\r\n\r\nOK\r\n";
        }
        String strResponseString2 = null;
        if (checkArgu(strArr, new String[]{"1", "1"})) {
            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "AT+NFCMTEST=1,1");
            startReceiver();
            ModuleNfc.sendIntentToGetTagId(this.context);
            return null;
        }
        int i = 0;
        if (checkArgu(strArr, new String[]{"1", "2"})) {
            String fromPath = "0";
            String fromPath2 = "0";
            File file = new File("data/log/NfcDetecting_cmd.log");
            File file2 = new File("data/log/NfcDetecting_ui.log");
            if (Support$Path.isExistFilePath(file.getPath())) {
                fromPath = Support$Path.readFromPath(file.getPath(), false);
                FtUtil.log_i(this.CLASS_NAME, "handleCommand", "Read Detecting from CMD = " + fromPath);
            }
            if (Support$Path.isExistFilePath(file2.getPath())) {
                fromPath2 = Support$Path.readFromPath(file2.getPath(), false);
                FtUtil.log_i(this.CLASS_NAME, "handleCommand", "Read Detecting from UI = " + fromPath2);
            }
            return responseString(strArr[0], fromPath + "," + fromPath2);
        }
        if (checkArgu(strArr, new String[]{"1", "3"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(1, 3));
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "5"})) {
            startReceiver();
            if (FtUtil.isFactoryBinary()) {
                sendNfcTestIntent(ModuleNfc.getNfcTestCommand(0, 5, this.context));
            } else {
                launchSemFactoryActivity(5);
            }
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "A"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommand(0, 10, this.context));
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "B"})) {
            startReceiver();
            launchSemFactoryActivity(11);
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "C"})) {
            startReceiver();
            launchSemFactoryActivity(12);
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "E"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommand(0, 14, this.context));
            return null;
        }
        if (checkArgu(strArr, new String[]{"7"})) {
            startReceiver();
            try {
                i = Integer.parseInt(strArr[1]);
            } catch (NumberFormatException unused) {
                FtUtil.log_i(this.CLASS_NAME, "handleCommand", "cnt format error : " + strArr[1]);
            }
            sendNfcTestIntent(ModuleNfc.getNfcTestCommand(7, i, this.context));
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "D"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV3(0, 13));
            return null;
        }
        if (checkArgu(strArr, new String[]{"9"})) {
            if (strArr[1].equals("1")) {
                Support$Path.set("FACM_NFC_TEST", "1");
                strArr = responseOK(strArr[0]);
            } else {
                String str = Support$Path.get("FACM_NFC_TEST");
                if ("Unknown".equals(str)) {
                    return responseNG(strArr[0]);
                }
                try {
                    String strValueOf = String.valueOf(Integer.parseInt(str) + 1);
                    if (strArr[1].equals(strValueOf)) {
                        Support$Path.set("FACM_NFC_TEST", strValueOf);
                        strArr = responseOK(strArr[0]);
                    } else {
                        strArr = responseNG(strArr[0]);
                    }
                } catch (NumberFormatException unused2) {
                    FtUtil.log_i(this.CLASS_NAME, "handleCommand", "parseInt => NumberFormatException");
                    strArr = responseNG(strArr[0]);
                }
            }
            return strArr;
        }
        if (checkArgu(strArr, new String[]{"0", "8"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 8));
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "9"})) {
            initNvRelatedNfc();
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 9));
            return null;
        }
        if (checkArgu(strArr, new String[]{"0", "0"})) {
            if (FtUtil.isFactoryBinary()) {
                startReceiver();
                sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 0));
            } else {
                strResponseString = pollingUntilNfcIsOff() ? responseOK(strArr[0]) : responseNG(strArr[0]);
                strResponseString2 = strResponseString;
            }
        } else if (checkArgu(strArr, new String[]{"0", "1"})) {
            this.mEndReceiver = false;
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 1));
        } else if (checkArgu(strArr, new String[]{"0", "2"})) {
            if (ModuleDevice.instance(this.context).isSupportSWP()) {
                startReceiver();
                sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 2));
            } else {
                strResponseString2 = "\r\n+" + this.CMD_NAME + ":" + strArr[0] + ",NA\r\n\r\nOK\r\n";
            }
        } else if (checkArgu(strArr, new String[]{"0", "3"})) {
            if (FtUtil.isFactoryBinary()) {
                startReceiver();
                sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(0, 3));
            } else {
                NfcStatus nfcStatusPollingUntilNfcIsOn = pollingUntilNfcIsOn(10);
                strResponseString = (nfcStatusPollingUntilNfcIsOn == NfcStatus.ON || nfcStatusPollingUntilNfcIsOn == NfcStatus.ENABLED) ? responseOK(strArr[0]) : responseNG(strArr[0]);
                strResponseString2 = strResponseString;
            }
        } else if (checkArgu(strArr, new String[]{"0", "4"})) {
            if (ModuleNfc.isSupportEseViaSpi(this.context)) {
                startReceiver();
                sendNfcTestIntent(ModuleNfc.getNfcTestCommand(0, 4, this.context));
            } else {
                strResponseString2 = "\r\n+" + this.CMD_NAME + ":" + strArr[0] + ",NA\r\n\r\nOK\r\n";
            }
        } else if (checkArgu(strArr, new String[]{"0", "6"})) {
            strResponseString2 = "\r\n+" + this.CMD_NAME + ":" + strArr[0] + ",NA\r\n\r\nOK\r\n";
        } else if (checkArgu(strArr, new String[]{"0", "7"})) {
            if (ModuleNfc.isSupportEseViaSpi(this.context)) {
                startReceiver();
                sendNfcTestIntent(ModuleNfc.getNfcTestCommand(0, 7, this.context));
            } else {
                strResponseString2 = "\r\n+" + this.CMD_NAME + ":" + strArr[0] + ",NA\r\n\r\nOK\r\n";
            }
        } else if (checkArgu(strArr, new String[]{"1", "0"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommandV2(1, 0));
        } else if (checkArgu(strArr, new String[]{"1", "4"})) {
            startReceiver();
            sendNfcTestIntent(ModuleNfc.getNfcTestCommand(1, 4, this.context));
            FtUtil.log_i(this.CLASS_NAME, "handleCommand", "1, 4");
        } else {
            if (checkArgu(strArr, new String[]{"1", "5"})) {
                if (!checkNfcInitPropValue()) {
                    return responseString(strArr[0], "NFC_INIT_FAILED");
                }
                FtUtil.log_d(this.CLASS_NAME, "handleCommand", "NFC is turning on");
                NfcStatus nfcStatusPollingUntilNfcIsOn2 = pollingUntilNfcIsOn(5);
                if (nfcStatusPollingUntilNfcIsOn2 != NfcStatus.OFF && nfcStatusPollingUntilNfcIsOn2 != NfcStatus.NONE) {
                    String t4tData = getT4tData(FILE_ID_PROP1);
                    strResponseString2 = "T4T_NOT_SUPPORTED".equals(t4tData) ? responseString(strArr[0], "NOT_SUPPORT") : responseString(strArr[0], t4tData);
                    if (this.mNfcAdapter != null && nfcStatusPollingUntilNfcIsOn2 == NfcStatus.ON) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "NFC is turning off");
                        this.mSamsungNfcAdapter.disable();
                    }
                }
                FtUtil.log_d(this.CLASS_NAME, "handleCommand", "Nfc didn't was on even though app requested to turn on nfc.");
                return responseString(strArr[0], "NFC_ON_FAILED");
            }
            if (checkArgu(strArr, new String[]{"1", "6"})) {
                strResponseString2 = responseString(strArr[0], ModuleDevice.instance(this.context).getSecureElement());
            } else {
                if (checkArgu(strArr, new String[]{"1", "7"})) {
                    String prop = Support$Path.getProp("nfc.bl.version");
                    strResponseString = "".equalsIgnoreCase(prop) ? responseString(strArr[0], "NONE") : responseString(strArr[0], prop);
                } else if (checkArgu(strArr, new String[]{"1", "8"})) {
                    String str2 = Support$Path.get("NFC_CHIP_NAME_PROP");
                    strResponseString = ("".equals(str2) || str2.split(",").length < 2) ? responseNG(strArr[0]) : responseString(strArr[0], str2);
                } else {
                    if (checkArgu(strArr, new String[]{"1", "9"})) {
                        return processToReadData(strArr[0], "CN", FILE_ID_PROP2);
                    }
                    if (checkArgu(strArr, new String[]{"1", "A"})) {
                        return processToReadData(strArr[0], "Data1", FILE_ID_PROP3);
                    }
                    if (checkArgu(strArr, new String[]{"1", "B"})) {
                        return processToReadData(strArr[0], "Data2", FILE_ID_PROP4);
                    }
                    if (checkArgu(strArr, new String[]{"2"})) {
                        String t4tData2 = setT4tData(strArr[1], FILE_ID_PROP1);
                        if ("OK".equals(t4tData2)) {
                            strResponseString2 = responseOK(strArr[0]);
                        } else if ("NG".equals(t4tData2)) {
                            strResponseString2 = responseNG(strArr[0]);
                        } else if ("T4T_NOT_SUPPORTED".equals(t4tData2)) {
                            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "IMEI write function is not supported.");
                            strResponseString2 = responseString(strArr[0], "NOT_SUPPORT");
                        }
                    } else if (checkArgu(strArr, new String[]{"3", "0"})) {
                        startReceiver();
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "Run APC");
                        this.context.sendBroadcast(ModuleNfc.getNfcTestCommandV3(3, 0), "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    } else if (checkArgu(strArr, new String[]{"3", "1"})) {
                        startReceiver();
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "Run APC");
                        this.context.sendBroadcast(ModuleNfc.getNfcTestCommandV3(3, 1), "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    } else if (checkArgu(strArr, new String[]{"3", "2"})) {
                        startReceiver();
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "S.LSI NFC F0 Test");
                        sendNfcTestIntent(ModuleNfc.getNfcTestCommandV3(3, 2));
                    } else if (checkArgu(strArr, new String[]{"3", "3"})) {
                        startReceiver();
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "NXP NFC F0 Test");
                        sendNfcTestIntent(ModuleNfc.getNfcTestCommandV3(3, 3));
                    } else if (checkArgu(strArr, new String[]{"3", "4"})) {
                        startReceiver();
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "NFC Bootloader & Firmware Update");
                        sendNfcTestIntent(ModuleNfc.getNfcTestCommandV3(3, 4));
                    } else if (checkArgu(strArr, new String[]{"3", "5"})) {
                        File file3 = new File("data/log/FelicaCal.log");
                        if (file3.exists()) {
                            String fromPath3 = Support$Path.readFromPath(file3.getPath(), true);
                            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "Read calData" + fromPath3);
                            strResponseString = responseString(strArr[0], fromPath3);
                        } else {
                            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "File is not existed.");
                            strResponseString = responseString(strArr[0], "NONE");
                        }
                    } else {
                        if (checkArgu(strArr, new String[]{"4"})) {
                            return processToWriteData(strArr[0], FILE_ID_PROP2, strArr[1], "CN");
                        }
                        if (checkArgu(strArr, new String[]{"5"})) {
                            return processToWriteData(strArr[0], FILE_ID_PROP3, strArr[1], "Data1");
                        }
                        if (checkArgu(strArr, new String[]{"6"})) {
                            return processToWriteData(strArr[0], FILE_ID_PROP4, strArr[1], "Data2");
                        }
                        AtCommandHandler.responseNA();
                        strResponseString2 = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                    }
                }
                strResponseString2 = strResponseString;
            }
        }
        return strResponseString2;
        throw th;
    }

    public final void initNvRelatedNfc() {
        setNfcTestNV(30);
        setNfcTestNV(72);
        setNfcTestNV(117);
        setNfcTestNV(69);
    }

    public final void launchSemFactoryActivity(int i) {
        try {
            Intent intent = new Intent();
            intent.setClassName("com.sem.factoryapp", "com.sem.factory.SemFactoryActivity");
            String packageName = getPackageName();
            FtUtil.log_d(this.CLASS_NAME, "launchSemFactoryActivity", "packageName : " + packageName);
            intent.putExtra("com.samsung.android.ese.test.extra.DATA_INTEGER", i);
            intent.putExtra("com.samsung.android.ese.test.extra.DATA_STRING", packageName);
            intent.setFlags(268435456);
            this.context.startActivity(intent);
        } catch (ActivityNotFoundException unused) {
            FtUtil.log_d(this.CLASS_NAME, "launchNfcActivity", "Activity Not Found");
        }
    }

    public final boolean pollingUntilNfcIsOff() {
        boolean z = true;
        if (this.mNfcAdapter != null) {
            this.mSamsungNfcAdapter.disable();
            int i = 0;
            while (this.mNfcAdapter.isEnabled()) {
                DigitizerElectricService$1$$ExternalSyntheticOutline0.m(i, "Check nfc count: ", this.CLASS_NAME, "pollingUntilNfcIsOff");
                FtUtil.Sleep.sleep(1000L);
                i++;
                if (i > 10) {
                    z = false;
                    break;
                }
            }
        }
        FtUtil.log_d(this.CLASS_NAME, "pollingUntilNfcIsOff", "Result : " + z);
        return z;
    }

    public final NfcStatus pollingUntilNfcIsOn(int i) {
        NfcStatus nfcStatus;
        NfcStatus nfcStatus2 = NfcStatus.NONE;
        if (this.mNfcAdapter == null) {
            FtUtil.log_d(this.CLASS_NAME, "pollingUntilNfcIsOn", "NfcAdapter is null");
            return nfcStatus2;
        }
        DigitizerElectricService$1$$ExternalSyntheticOutline0.m(i, "Max TimeOut : ", this.CLASS_NAME, "pollingUntilNfcIsOn");
        if (this.mNfcAdapter.isEnabled()) {
            nfcStatus = NfcStatus.ENABLED;
        } else {
            this.mSamsungNfcAdapter.enable();
            FtUtil.Sleep.sleep(1000L);
            NfcStatus nfcStatus3 = NfcStatus.ON;
            int i2 = 0;
            while (!this.mNfcAdapter.isEnabled()) {
                DigitizerElectricService$1$$ExternalSyntheticOutline0.m(i2, "Check nfc count: ", this.CLASS_NAME, "pollingUntilNfcIsOn");
                FtUtil.Sleep.sleep(1000L);
                i2++;
                if (i2 > i) {
                    nfcStatus = NfcStatus.OFF;
                }
            }
            nfcStatus = nfcStatus3;
        }
        FtUtil.log_d(this.CLASS_NAME, "pollingUntilNfcIsOn", "result : " + nfcStatus);
        return nfcStatus;
    }

    public final String processToReadData(String str, String str2, byte[] bArr) {
        FtUtil.log_d(this.CLASS_NAME, "processToReadData", "Reading type : ".concat(str2));
        String t4tData = getT4tData(bArr);
        if ("T4T_NOT_SUPPORTED".equals(t4tData)) {
            return responseString(str, "NOT_SUPPORT");
        }
        return "".equals(t4tData) ? responseNG(str) : responseString(str, t4tData);
    }

    public final String processToWriteData(String str, byte[] bArr, String str2, String str3) {
        FtUtil.log_d(this.CLASS_NAME, "processToWriteData", "Writing type : ".concat(str3));
        String t4tData = setT4tData(str2, bArr);
        if ("OK".equals(t4tData)) {
            return responseOK(str);
        }
        if ("NG".equals(t4tData)) {
            return responseNG(str);
        }
        return "T4T_NOT_SUPPORTED".equals(t4tData) ? responseString(str, "NOT_SUPPORT") : responseNG(str);
    }

    /* JADX WARN: Type inference failed for: r0v0, types: [android.os.Handler, com.sec.facatfunction.aporiented.athandler.AtNfcmtest$2] */
    public final void sendNfcTestIntent(final Intent intent) {
        ?? r0 = new Handler(this.context.getMainLooper()) { // from class: com.sec.facatfunction.aporiented.athandler.AtNfcmtest.2
            @Override // android.os.Handler
            public final void handleMessage(Message message) {
                AtNfcmtest atNfcmtest = AtNfcmtest.this;
                atNfcmtest.context.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                FtUtil.log_d(atNfcmtest.CLASS_NAME, "sendNfcTestIntent");
            }
        };
        this.mNfcTestHandler = r0;
        r0.sendEmptyMessageDelayed(0, 1400L);
    }

    public final void setNfcTestNV(int i) {
        FtUtil.log_d(this.CLASS_NAME, "setTSPTestNV", "NV = " + i + ", itemResult = 78");
        NVAccessor.setNV(i, (byte) 78);
    }

    public final String setT4tData(String str, byte[] bArr) {
        int iIntValue;
        if (!ModuleNfc.isSupportT4t(this.context)) {
            return "T4T_NOT_SUPPORTED";
        }
        byte[] bytes = str.getBytes(StandardCharsets.UTF_8);
        Context context = this.context;
        int iBytesToInt = bytesToInt(bArr);
        NfcAdapter defaultAdapter = !context.getPackageManager().hasSystemFeature("android.hardware.nfc") ? null : NfcAdapter.getDefaultAdapter(context);
        int i = -1;
        if (defaultAdapter == null) {
            iIntValue = -1;
        } else {
            try {
                Class[] clsArr = new Class[0];
                Method declaredMethod = NfcAdapter.class.getDeclaredMethod("getNfcOemExtension", null);
                declaredMethod.setAccessible(true);
                Object objInvoke = declaredMethod.invoke(defaultAdapter, null);
                Class[] clsArr2 = new Class[0];
                Method declaredMethod2 = objInvoke.getClass().getDeclaredMethod("getT4tNdefNfcee", null);
                declaredMethod2.setAccessible(true);
                Object objInvoke2 = declaredMethod2.invoke(objInvoke, null);
                iIntValue = ((Integer) objInvoke2.getClass().getDeclaredMethod("writeData", Integer.TYPE, byte[].class).invoke(objInvoke2, Integer.valueOf(iBytesToInt), bytes)).intValue();
            } catch (Exception e) {
                e.printStackTrace();
                iIntValue = -1;
            }
        }
        DigitizerElectricService$1$$ExternalSyntheticOutline0.m(iIntValue, "status : ", this.CLASS_NAME, "setT4tData");
        try {
            i = Class.forName("android.nfc.T4tNdefNfcee").getDeclaredField("WRITE_DATA_SUCCESS").getInt(null);
        } catch (Exception e2) {
            e2.printStackTrace();
        }
        if (iIntValue == i) {
            FtUtil.log_d(this.CLASS_NAME, "setT4tData", "Nfc T4T Write success");
            return "OK";
        }
        FtUtil.log_d(this.CLASS_NAME, "setT4tData", "Nfc T4T Write fail");
        return "NG";
    }

    public final void startReceiver() {
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("com.sec.android.app.nfcntest.NFC_TEST_RESPONSE");
        intentFilter.addAction("com.sec.android.app.nfctest.NFC_TEST_RESPONSE_V2");
        intentFilter.addAction("com.sec.android.app.nfctest.NFC_TEST_RESPONSE_V3");
        intentFilter.addAction("com.samsung.android.nfc.action.STOP_APC_RESP");
        intentFilter.addAction("com.samsung.android.nfc.test.action.RESPONSE");
        intentFilter.addAction("com.samsung.android.ese.test.action.RESPONSE");
        this.context.registerReceiver(this.mReceiver, intentFilter, "com.samsung.permission.NFC_SYSTEM_PROTECTION", null, 2);
    }
}
