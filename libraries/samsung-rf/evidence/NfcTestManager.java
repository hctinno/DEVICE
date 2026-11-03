package com.samsung.android.nfc.testapp;

import android.app.ActivityManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.nfc.IAppCallback;
import android.nfc.INfcAdapter;
import android.nfc.NfcAdapter;
import android.nfc.NfcOemExtension;
import android.nfc.Tag;
import android.os.Binder;
import android.os.Bundle;
import android.os.FactoryTest;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemProperties;
import android.os.UserHandle;
import android.sysprop.NfcProperties;
import com.samsung.android.nfc.core.SamsungExtension;
import com.samsung.android.nfc.core.oem.GeneralCallback;
import com.samsung.android.nfc.feature.Properties;
import com.samsung.android.nfc.firmware.Firmware;
import com.samsung.android.nfc.firmware.FirmwareVersion;
import com.samsung.android.nfc.log.Log;
import com.samsung.android.nfc.nci.SamsungNciTransportManager;
import com.samsung.android.nfc.nci.cmd.factory.GetResoFreqCommand;
import com.samsung.android.nfc.nci.cmd.factory.GetSwpStatusCommand;
import com.samsung.android.nfc.nci.cmd.factory.PrbsCommand;
import com.samsung.android.nfc.nci.cmd.factory.SelectPreferredPortCommand;
import com.samsung.android.nfc.util.NfcUtil;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Iterator;
import java.util.StringJoiner;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.FutureTask;

/* JADX INFO: loaded from: classes.dex */
public class NfcTestManager implements GeneralCallback {
    static final boolean DBG = ((Boolean) NfcProperties.debug_enabled().orElse(Boolean.TRUE)).booleanValue();
    private static final IBinder nfcInterfaceToken = new Binder();
    private Context mContext;
    private EventHandler mEventHandler;
    Firmware mFirmware;
    SamsungNciTransportManager mNciTransportManager;
    NfcAdapter mNfcAdapter;
    NfcOemExtension mNfcOemExtension;
    private int mState;
    private boolean mTestMode = false;
    private boolean mDiscoverOff = false;
    private boolean mListenActivated = false;
    private NfcTestAtCommand mNfcTestAtCommand = null;
    boolean mIsPrbsStarted = false;
    boolean mSkipEnableAfterPrbs = false;
    byte mPrbsTech = 0;
    byte mPrbsRate = 0;
    private boolean mEnableDiscoveryPending = false;
    private boolean mDisableDiscoveryPending = false;
    private final BroadcastReceiver mReceiver = new AnonymousClass2();
    private final BroadcastReceiver mReceiverWithoutPerm = new AnonymousClass3();

    private void disableReaderModeIfNeeded() {
    }

    byte getRate(int i) {
        if (i == 0) {
            return (byte) 1;
        }
        if (i == 1) {
            return (byte) 2;
        }
        return i == 2 ? (byte) 3 : (byte) 1;
    }

    byte getTech(int i) {
        if (i == 0) {
            return (byte) 1;
        }
        if (i == 1) {
            return (byte) 2;
        }
        return i == 2 ? (byte) 3 : (byte) 1;
    }

    @Override // com.samsung.android.nfc.core.oem.GeneralCallback
    public void onStateUpdated(int i) {
        this.mState = i;
        if (i == 1 && this.mIsPrbsStarted) {
            startPrbs();
        }
    }

    private void startPrbs() {
        if (this.mState != 1) {
            Log.d("NfcTestManager", "PRBS is only allowed in NFC off");
            return;
        }
        this.mNfcAdapter.registerControllerAlwaysOnListener(Executors.newSingleThreadExecutor(), new AnonymousClass1());
        this.mNfcOemExtension.setControllerAlwaysOnMode(2);
    }

    /* JADX INFO: renamed from: com.samsung.android.nfc.testapp.NfcTestManager$1, reason: invalid class name */
    class AnonymousClass1 implements NfcAdapter.ControllerAlwaysOnListener {
        AnonymousClass1() {
        }

        public void onControllerAlwaysOnChanged(boolean z) {
            Log.d("NfcTestManager", "always on isEnabled = " + z);
            if (z) {
                NfcTestManager nfcTestManager = NfcTestManager.this;
                nfcTestManager.mNciTransportManager.sendVendorNciMessageAsync(PrbsCommand.create((byte) 1, nfcTestManager.mPrbsTech, nfcTestManager.mPrbsRate), new SamsungNciTransportManager.AsyncCallback() { // from class: com.samsung.android.nfc.testapp.NfcTestManager$1$$ExternalSyntheticLambda0
                    @Override // com.samsung.android.nfc.nci.SamsungNciTransportManager.AsyncCallback
                    public final void callback(byte[] bArr) {
                        this.f$0.lambda$onControllerAlwaysOnChanged$0(bArr);
                    }
                });
            } else {
                NfcTestManager nfcTestManager2 = NfcTestManager.this;
                if (!nfcTestManager2.mSkipEnableAfterPrbs) {
                    nfcTestManager2.mNfcAdapter.enable();
                }
                NfcTestManager.this.mNfcAdapter.unregisterControllerAlwaysOnListener(this);
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public /* synthetic */ void lambda$onControllerAlwaysOnChanged$0(byte[] bArr) {
            Log.d("NfcTestManager", "prbs payload = " + NfcUtil.bytesToString(bArr));
            NfcTestManager nfcTestManager = NfcTestManager.this;
            nfcTestManager.mIsPrbsStarted = false;
            nfcTestManager.mPrbsTech = (byte) 0;
            nfcTestManager.mPrbsRate = (byte) 0;
        }
    }

    boolean isNfcEnabled() {
        return this.mState == 3;
    }

    public NfcTestManager(Context context, Firmware firmware) {
        this.mContext = context;
        initialize();
        this.mFirmware = firmware;
        this.mNciTransportManager = SamsungNciTransportManager.getInstance();
        NfcAdapter nfcAdapter = NfcAdapter.getNfcAdapter(this.mContext);
        this.mNfcAdapter = nfcAdapter;
        this.mNfcOemExtension = nfcAdapter.getNfcOemExtension();
        this.mEventHandler = new EventHandler(Looper.getMainLooper());
    }

    private void initialize() {
        Log.i("NfcTestManager", "initialize NfcTestManager");
        if (FactoryTest.isFactoryBinary()) {
            this.mNfcTestAtCommand = new NfcTestAtCommand(this.mContext);
        }
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("com.samsung.android.nfc.test.action.REQUEST");
        Context context = this.mContext;
        BroadcastReceiver broadcastReceiver = this.mReceiver;
        UserHandle userHandle = UserHandle.ALL;
        context.registerReceiverAsUser(broadcastReceiver, userHandle, intentFilter, "com.samsung.permission.NFC_SYSTEM_PROTECTION", null, 2);
        IntentFilter intentFilter2 = new IntentFilter();
        intentFilter2.addAction("services.nfc.action.GET_FIRMWARE_VERSION");
        this.mContext.registerReceiverAsUser(this.mReceiverWithoutPerm, userHandle, intentFilter2, null, null, 2);
    }

    public boolean isNfcTestModeEnabled() {
        return this.mTestMode;
    }

    public boolean isDiscoverOff() {
        return this.mDiscoverOff;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResponse(String str, String[] strArr, String[] strArr2, String str2) {
        Intent intent = new Intent(str);
        intent.setFlags(268435456);
        for (int i = 0; i < strArr.length; i++) {
            intent.putExtra(strArr[i], strArr2[i]);
        }
        if (str2 != null && str2.length() > 0) {
            intent.setPackage(str2);
            this.mContext.sendBroadcast(intent);
        } else {
            Log.w("NfcTestManager", "can't send response");
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResponse(int i, String str, int i2) {
        Intent intent = new Intent("com.samsung.android.nfc.test.action.RESPONSE");
        intent.setFlags(268435456);
        intent.putExtra("com.samsung.android.nfc.test.extra.ID", i);
        intent.putExtra(str, i2);
        this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResponse(int i, String str, String str2) {
        Intent intent = new Intent("com.samsung.android.nfc.test.action.RESPONSE");
        intent.setFlags(268435456);
        intent.putExtra("com.samsung.android.nfc.test.extra.ID", i);
        intent.putExtra(str, str2);
        this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResponse(int i, String[] strArr, String[] strArr2, String str) {
        Intent intent = new Intent("com.samsung.android.nfc.test.action.RESPONSE");
        intent.setFlags(268435456);
        intent.putExtra("com.samsung.android.nfc.test.extra.ID", i);
        for (int i2 = 0; i2 < strArr.length; i2++) {
            intent.putExtra(strArr[i2], strArr2[i2]);
        }
        if (str != null && str.length() > 0) {
            intent.setPackage(str);
            this.mContext.sendBroadcast(intent);
        } else {
            Log.w("NfcTestManager", "can't send response");
        }
    }

    public void onSeListenModeStateChanged(boolean z) {
        synchronized (this) {
            this.mListenActivated = z;
            Log.d("NfcTestManager", "mListenActivated: " + this.mListenActivated);
        }
        if (!FactoryTest.isFactoryBinary() || this.mListenActivated) {
            return;
        }
        handlePendingDiscovery();
    }

    private void handlePendingDiscovery() {
        if (this.mEnableDiscoveryPending && !isPollingSkipRequired()) {
            Log.d("NfcTestManager", "handlePendingDiscovery(Enable)");
            enableDiscovery();
        }
        if (this.mDisableDiscoveryPending && isPollingSkipRequired()) {
            Log.d("NfcTestManager", "handlePendingDiscovery(Disable)");
            disableDiscovery();
        }
        this.mEnableDiscoveryPending = false;
        this.mDisableDiscoveryPending = false;
    }

    public static boolean isFactoryTestAppRunning(Context context) {
        if (Properties.isShipProduct()) {
            return false;
        }
        try {
            String className = ((ActivityManager) context.getSystemService("activity")).getRunningTasks(1).get(0).topActivity.getClassName();
            StringBuilder sb = new StringBuilder();
            sb.append("Top activity class: ");
            sb.append(className == null ? "null" : className);
            Log.d("NfcTestManager", sb.toString());
            return className != null && (className.contains("com.sec.facuifunction") || className.contains("com.sec.facatfunction") || className.contains("com.samsung.android.aircommandmanager"));
        } catch (Exception e) {
            Log.e("NfcTestManager", "Exception: " + e);
        }
    }

    public void notifyEeListenActivated(boolean z) {
        sendEventMessage(1, Boolean.valueOf(z));
    }

    private void sendEventMessage(int i, Object obj) {
        Message messageObtainMessage = this.mEventHandler.obtainMessage();
        messageObtainMessage.what = i;
        messageObtainMessage.obj = obj;
        this.mEventHandler.sendMessage(messageObtainMessage);
    }

    final class EventHandler extends Handler {
        public EventHandler(Looper looper) {
            super(looper);
            Log.d("NfcTestManager", "EventHandler is started");
        }

        @Override // android.os.Handler
        public void handleMessage(Message message) {
            if (message.what != 1) {
                return;
            }
            boolean zBooleanValue = ((Boolean) message.obj).booleanValue();
            Log.d("NfcTestManager", "MSG_EE_LISTEN_ACTIVATED, isActivated: " + zBooleanValue);
            NfcTestManager.this.onSeListenModeStateChanged(zBooleanValue);
        }
    }

    /* JADX INFO: renamed from: com.samsung.android.nfc.testapp.NfcTestManager$2, reason: invalid class name */
    class AnonymousClass2 extends BroadcastReceiver {
        AnonymousClass2() {
        }

        @Override // android.content.BroadcastReceiver
        public void onReceive(final Context context, final Intent intent) {
            String action = intent.getAction();
            if (action == null) {
                return;
            }
            final int intExtra = intent.getIntExtra("com.samsung.android.nfc.test.extra.ID", -1);
            Log.d("NfcTestManager", "action: " + action);
            Log.d("NfcTestManager", "ID: " + NfcTestManager.getNfcTestRequestActionExtraIdString(intExtra));
            if (!action.equals("com.samsung.android.nfc.test.action.REQUEST")) {
                Log.d("NfcTestManager", "mReceiver: Unexpected action received : " + action);
                return;
            }
            new Thread(new Runnable() { // from class: com.samsung.android.nfc.testapp.NfcTestManager$2$$ExternalSyntheticLambda0
                @Override // java.lang.Runnable
                public final void run() {
                    this.f$0.lambda$onReceive$0(intExtra, intent, context);
                }
            }).start();
        }

        /* JADX INFO: Access modifiers changed from: private */
        public /* synthetic */ void lambda$onReceive$0(int i, Intent intent, Context context) {
            switch (i) {
                case 0:
                    NfcTestManager.this.mTestMode = true;
                    NfcTestManager.this.mDiscoverOff = false;
                    break;
                case 1:
                    NfcTestManager.this.mTestMode = false;
                    NfcTestManager.this.mDiscoverOff = true;
                    break;
                case 2:
                    NfcTestManager.this.enableDiscovery();
                    break;
                case 3:
                    NfcTestManager.this.disableDiscovery();
                    break;
                case 4:
                    NfcTestManager.this.mDiscoverOff = true;
                    break;
                case 5:
                    NfcTestManager nfcTestManager = NfcTestManager.this;
                    nfcTestManager.sendResponse(5, "com.samsung.android.nfc.test.extra.DATA", nfcTestManager.getSwpState(2));
                    break;
                case 6:
                    NfcTestManager nfcTestManager2 = NfcTestManager.this;
                    nfcTestManager2.sendResponse(6, "com.samsung.android.nfc.test.extra.DATA", nfcTestManager2.getSwpState(1));
                    break;
                case 7:
                    checkCardModeState();
                    break;
                default:
                    switch (i) {
                        case 9:
                            checkFirmwareVersion(intent);
                            break;
                        case 10:
                            try {
                                NfcAdapter.getDefaultAdapter(context).enable();
                            } catch (Exception e) {
                                e.printStackTrace();
                                return;
                            }
                            break;
                        case 11:
                            NfcTestManager.this.enableDiscovery();
                            NfcTestManager.this.notifyNfcService(true);
                            break;
                        case 12:
                            NfcTestManager.this.notifyNfcService(false);
                            NfcTestManager.this.disableDiscovery();
                            break;
                        default:
                            switch (i) {
                                case 21:
                                    break;
                                case 22:
                                    intent.getIntExtra("com.samsung.android.nfc.test.extra.CMD", -1);
                                    intent.getIntExtra("com.samsung.android.nfc.test.extra.DATA_INTEGER", -1);
                                    break;
                                case 23:
                                    processIndicationV3Command(intent);
                                    break;
                                default:
                                    switch (i) {
                                        case 31:
                                            NfcTestManager.this.startPrbs(intent.getIntExtra("com.samsung.android.nfc.test.extra.TECH", 0), intent.getIntExtra("com.samsung.android.nfc.test.extra.RATE", 0));
                                            break;
                                        case 32:
                                            NfcTestManager.this.stopPrbs();
                                            break;
                                        case 33:
                                            NfcTestManager.this.mFirmware.startFirmwareForceDownload();
                                            break;
                                        case 34:
                                            Log.d("NfcTestManager", "SET_TECH_MASK: " + intent.getIntExtra("com.samsung.android.nfc.test.extra.TECH", 0));
                                            NfcTestManager.this.sendResponse(34, "com.samsung.android.nfc.test.extra.DATA", 1);
                                            break;
                                        case 35:
                                            int intExtra = intent.getIntExtra("com.samsung.android.nfc.test.extra.DATA", 0);
                                            if (intExtra == 1) {
                                                SystemProperties.set("csa.nfc.offset", "1");
                                            } else if (intExtra == 2) {
                                                SystemProperties.set("csa.nfc.offset", "2");
                                            } else if (intExtra == 3) {
                                                SystemProperties.set("csa.nfc.offset", "3");
                                            }
                                            NfcTestManager.this.sendResponse(35, "com.samsung.android.nfc.test.extra.DATA", 1);
                                            break;
                                        case 36:
                                            NfcTestManager.this.sendResponse(36, "com.samsung.android.nfc.test.extra.DATA", SystemProperties.get("csa.nfc.offset"));
                                            break;
                                        default:
                                            Log.e("NfcTestManager", "No ID! Please check request action!");
                                            break;
                                    }
                                    break;
                            }
                            break;
                    }
                    break;
            }
        }

        private void checkCardModeState() {
            boolean z;
            synchronized (NfcTestManager.this) {
                z = NfcTestManager.this.mListenActivated;
            }
            NfcTestManager.this.sendResponse(7, "com.samsung.android.nfc.test.extra.RESULT", z ? 1 : 0);
        }

        private void checkFirmwareVersion(Intent intent) {
            String[] strArr = {"com.samsung.android.nfc.test.extra.VENDOR", "com.samsung.android.nfc.test.extra.VERSION"};
            String[] strArr2 = {"", ""};
            String vendorName = FirmwareVersion.getVendorName();
            String firmwareVersion = FirmwareVersion.getFirmwareVersion();
            String rfVersion = FirmwareVersion.getRfVersion();
            if (rfVersion != null && rfVersion.length() > 0) {
                firmwareVersion = firmwareVersion + "." + rfVersion;
            }
            String stringExtra = intent.getStringExtra("com.samsung.android.nfc.test.extra.PACKAGE");
            strArr2[0] = vendorName;
            strArr2[1] = firmwareVersion;
            NfcTestManager.this.sendResponse(9, strArr, strArr2, stringExtra);
        }

        private void processIndicationV3Command(Intent intent) {
            int intExtra = intent.getIntExtra("com.samsung.android.nfc.test.extra.CMD", -1);
            int intExtra2 = intent.getIntExtra("com.samsung.android.nfc.test.extra.DATA_INTEGER", -1);
            if (intExtra == -1 || intExtra2 == -1) {
                return;
            }
            if (intExtra == 0) {
                if (intExtra2 == 13) {
                    processCheckEuiccStatus(intExtra);
                }
            } else {
                if (intExtra != 3) {
                    Log.e("NfcTestManager", "Not allowed command set");
                    return;
                }
                if (intExtra2 == 2) {
                    processGetSelfF0Command(intExtra, intExtra2);
                } else if (intExtra2 == 3) {
                    NfcTestManager.this.mNfcAdapter.registerControllerAlwaysOnListener(Executors.newSingleThreadExecutor(), new AnonymousClass1(intExtra));
                    NfcTestManager.this.mNfcOemExtension.setControllerAlwaysOnMode(2);
                }
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.nfc.testapp.NfcTestManager$2$1, reason: invalid class name */
        class AnonymousClass1 implements NfcAdapter.ControllerAlwaysOnListener {
            final /* synthetic */ int val$cmdId;

            AnonymousClass1(int i) {
                this.val$cmdId = i;
            }

            public void onControllerAlwaysOnChanged(boolean z) {
                Log.d("NfcTestManager", "always on isEnabled = " + z);
                if (z) {
                    SamsungNciTransportManager samsungNciTransportManager = NfcTestManager.this.mNciTransportManager;
                    GetResoFreqCommand getResoFreqCommandCreate = GetResoFreqCommand.create();
                    final int i = this.val$cmdId;
                    samsungNciTransportManager.sendVendorNciMessageAsync(getResoFreqCommandCreate, new SamsungNciTransportManager.AsyncCallback() { // from class: com.samsung.android.nfc.testapp.NfcTestManager$2$1$$ExternalSyntheticLambda0
                        @Override // com.samsung.android.nfc.nci.SamsungNciTransportManager.AsyncCallback
                        public final void callback(byte[] bArr) {
                            this.f$0.lambda$onControllerAlwaysOnChanged$0(i, bArr);
                        }
                    });
                    return;
                }
                NfcTestManager.this.mNfcAdapter.unregisterControllerAlwaysOnListener(this);
            }

            /* JADX INFO: Access modifiers changed from: private */
            public /* synthetic */ void lambda$onControllerAlwaysOnChanged$0(int i, byte[] bArr) {
                Log.d("NfcTestManager", "freq payload = " + NfcUtil.bytesToString(bArr));
                StringBuilder sb = new StringBuilder();
                if (bArr.length == 6 && bArr[0] == 34 && bArr[1] == 0) {
                    ByteBuffer byteBufferWrap = ByteBuffer.wrap(bArr, 2, bArr.length - 2);
                    sb.append("OK");
                    sb.append(",");
                    sb.append(Integer.toString(byteBufferWrap.getShort()));
                    sb.append(",");
                    sb.append(Integer.toString(byteBufferWrap.getShort()));
                } else {
                    sb.append("NG");
                }
                String string = sb.toString();
                Log.d("NfcTestManager", "Resonant Frequency from CLF : " + string);
                if (string.contains("OK")) {
                    Properties.setSelfF0Result(string);
                }
                NfcTestManager.this.sendResponseData(i, string);
                NfcTestManager.this.mNfcOemExtension.setControllerAlwaysOnMode(0);
            }
        }

        private void processCheckEuiccStatus(final int i) {
            Executors.newSingleThreadExecutor().submit(new FutureTask(new Callable() { // from class: com.samsung.android.nfc.testapp.NfcTestManager$2$$ExternalSyntheticLambda1
                @Override // java.util.concurrent.Callable
                public final Object call() {
                    return this.f$0.lambda$processCheckEuiccStatus$1(i);
                }
            }));
        }

        /* JADX INFO: Access modifiers changed from: private */
        public /* synthetic */ Boolean lambda$processCheckEuiccStatus$1(int i) {
            StringJoiner stringJoiner = new StringJoiner(",");
            StringJoiner stringJoiner2 = new StringJoiner("_");
            if (SystemProperties.getBoolean("ro.nfc.euicc_supported", false)) {
                Iterator it = Arrays.asList(5, 6).iterator();
                boolean z = true;
                int i2 = 1;
                while (it.hasNext()) {
                    int iIntValue = ((Integer) it.next()).intValue();
                    Log.e("NfcTestManager", "check EUICC" + i2);
                    if (!checkEuiccStatus(iIntValue)) {
                        stringJoiner2.add("eSIM" + i2);
                        z = false;
                    } else {
                        stringJoiner2.add("PASS");
                    }
                    i2++;
                }
                stringJoiner.add(z ? "OK" : "NG").add(stringJoiner2.toString());
            } else {
                Log.e("NfcTestManager", "EUICC-SWP is not supported");
                stringJoiner.add("NA");
            }
            Log.d("NfcTestManager", "EUICC-SWP: " + stringJoiner.toString());
            Intent intent = new Intent("com.samsung.android.nfc.test.action.RESPONSE");
            intent.putExtra("com.samsung.android.nfc.test.extra.ID", 23);
            intent.putExtra("com.samsung.android.nfc.test.extra.CMD", i);
            intent.putExtra("com.samsung.android.nfc.test.extra.DATA_STRING", stringJoiner.toString());
            intent.setPackage("com.sec.facatfunction");
            NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
            intent.setPackage("com.sec.facuifunction");
            NfcTestManager.this.mContext.sendBroadcast(intent);
            return Boolean.TRUE;
        }

        private boolean checkEuiccStatus(int i) {
            return NfcTestManager.this.assignSwp(NfcTestManager.getEuiccPortNumber(i)) && NfcTestManager.this.getSwpState(i) == 1;
        }

        private void processGetSelfF0Command(int i, int i2) {
            Log.d("NfcTestManager", "processGetSelfF0Command() : " + i2);
            byte[] resonantFrequencyFromClf = NfcTestManager.this.getResonantFrequencyFromClf();
            Log.d("NfcTestManager", "freq payload = " + NfcUtil.bytesToString(resonantFrequencyFromClf));
            StringBuilder sb = new StringBuilder();
            if (resonantFrequencyFromClf.length == 6 && resonantFrequencyFromClf[0] == 34 && resonantFrequencyFromClf[1] == 0) {
                ByteBuffer byteBufferWrap = ByteBuffer.wrap(resonantFrequencyFromClf, 2, resonantFrequencyFromClf.length - 2);
                sb.append("OK");
                sb.append(",");
                sb.append(Integer.toString(byteBufferWrap.getShort()));
            } else {
                sb.append("NG");
            }
            String string = sb.toString();
            Log.d("NfcTestManager", "Resonant Frequency from CLF : " + string);
            if (string.contains("OK")) {
                Properties.setSelfF0Result(string);
            }
            NfcTestManager.this.sendResponseData(i, string);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void sendResponseData(int i, String str) {
        if (str.contains("OK")) {
            Properties.setSelfF0Result(str);
        }
        Intent intent = new Intent("com.samsung.android.nfc.test.action.RESPONSE");
        intent.putExtra("com.samsung.android.nfc.test.extra.ID", 23);
        intent.putExtra("com.samsung.android.nfc.test.extra.CMD", i);
        intent.putExtra("com.samsung.android.nfc.test.extra.DATA_STRING", str);
        intent.setPackage("com.sec.facatfunction");
        this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
        intent.setPackage("com.sec.facuifunction");
        this.mContext.sendBroadcast(intent);
        intent.setPackage("com.sec.android.app.nfctest");
        this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
        intent.setPackage("com.sec.nfc.felicalocktest");
        this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Code duplicated, block: B:10:0x0010  */
    public static int getEuiccPortNumber(int i) {
        int i2;
        if (!NfcUtil.isNxpChip()) {
            i2 = i;
        } else if (i == 5) {
            i2 = 0;
        } else if (i == 6) {
            i2 = 1;
        } else {
            i2 = i;
        }
        Log.e("NfcTestManager", "swp_id(" + i + ") to port( " + i2 + ")");
        return i2;
    }

    /* JADX INFO: renamed from: com.samsung.android.nfc.testapp.NfcTestManager$3, reason: invalid class name */
    class AnonymousClass3 extends BroadcastReceiver {
        AnonymousClass3() {
        }

        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, final Intent intent) {
            final String action = intent.getAction();
            Log.d("NfcTestManager", "action: " + action);
            if (action != null && action.equals("services.nfc.action.GET_FIRMWARE_VERSION")) {
                new Thread(new Runnable() { // from class: com.samsung.android.nfc.testapp.NfcTestManager$3$$ExternalSyntheticLambda0
                    @Override // java.lang.Runnable
                    public final void run() {
                        this.f$0.lambda$onReceive$0(intent, action);
                    }
                }).start();
            }
        }

        /* JADX INFO: Access modifiers changed from: private */
        public /* synthetic */ void lambda$onReceive$0(Intent intent, String str) {
            try {
                String[] strArr = {"", ""};
                String vendorName = FirmwareVersion.getVendorName();
                String firmwareVersion = FirmwareVersion.getFirmwareVersion();
                String stringExtra = intent.getStringExtra("package");
                strArr[0] = vendorName;
                strArr[1] = firmwareVersion;
                NfcTestManager.this.sendResponse("services.nfc.action.GET_FIRMWARE_VERSION_RESPONSE", new String[]{"vendor", "version"}, strArr, stringExtra);
            } catch (Exception e) {
                Log.e("NfcTestManager", "Action: " + str, e);
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void notifyNfcService(boolean z) {
        INfcAdapter iNfcAdapterAsInterface = INfcAdapter.Stub.asInterface(ServiceManager.getService("nfc"));
        int i = z ? (this.mContext.getPackageManager().hasSystemFeature("com.samsung.android.nfc.gpfelica") ? 4 : 1) | 128 : 0;
        if (DBG) {
            Log.v("NfcTestManager", "Setting NFC reader mode to flags " + i + " pkg name = " + this.mContext.getPackageName());
        }
        try {
            iNfcAdapterAsInterface.setReaderMode(nfcInterfaceToken, new IAppCallback() { // from class: com.samsung.android.nfc.testapp.NfcTestManager.4
                public IBinder asBinder() {
                    return null;
                }

                public void onTagDiscovered(Tag tag) {
                    Log.d("NfcTestManager", "tag detected in Test mode");
                    Intent intent = new Intent("com.samsung.android.nfc.test.action.TAG_DISCOVERED");
                    intent.setPackage("com.android.nfc");
                    NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    intent.setPackage("com.sec.facatfunction");
                    NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    intent.setPackage("com.samsung.android.nfc");
                    NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    intent.setPackage("com.sec.facuifunction");
                    NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                    intent.setPackage("com.sec.android.app.nfctest");
                    NfcTestManager.this.mContext.sendBroadcast(intent, "com.samsung.permission.NFC_SYSTEM_PROTECTION");
                }
            }, i, (Bundle) null, this.mContext.getPackageName());
        } catch (RemoteException e) {
            Log.w("NfcTestManager", "Could not notify NFC service, remote exception: " + e);
        }
    }

    public void enableDiscovery() {
        if (!isNfcEnabled()) {
            Log.d("NfcTestManager", "Skip due to NFC off");
            return;
        }
        if (this.mListenActivated && FactoryTest.isFactoryBinary()) {
            Log.e("NfcTestManager", "Listen mode is activated state so postpone enableDiscovery util it is deactivated");
            this.mEnableDiscoveryPending = true;
        } else {
            Log.d("NfcTestManager", "setReaderModePollingEnabled is true");
            NfcAdapter.getDefaultAdapter(this.mContext);
        }
    }

    public void disableDiscovery() {
        if (!isNfcEnabled()) {
            Log.d("NfcTestManager", "Skip due to NFC off");
            return;
        }
        if (this.mListenActivated && FactoryTest.isFactoryBinary()) {
            Log.e("NfcTestManager", "Listen mode is activated state, so postpone disableDiscovery util it is deactivated");
            this.mDisableDiscoveryPending = true;
        } else {
            Log.d("NfcTestManager", "setReaderModePollingEnabled is false");
            NfcAdapter.getDefaultAdapter(this.mContext);
        }
    }

    public boolean assignSwp(int i) {
        this.mNfcOemExtension.pausePolling(1000L);
        byte[] bArrSendVendorNciMessage = this.mNciTransportManager.sendVendorNciMessage(SelectPreferredPortCommand.create((byte) i));
        boolean z = false;
        if (bArrSendVendorNciMessage[0] == 35 && bArrSendVendorNciMessage[1] == 0) {
            z = true;
        }
        this.mNfcOemExtension.resumePolling();
        if (z) {
            SamsungExtension.getInstance().runEnableDisableTaskWithLocked(new int[]{2, 1});
            return z;
        }
        Log.e("NfcTestManager", "Assign SWP(EUICC) fail due to something reason");
        return z;
    }

    public int getSwpState(int i) {
        try {
            Thread.sleep(30L);
        } catch (Exception e) {
            Log.e("NfcTestManager", "Exception occurred in getSwpState method", e);
        }
        if (!isNfcEnabled()) {
            Log.d("NfcTestManager", "Skip due to NFC off");
            return -1;
        }
        byte[] bArrSendVendorNciMessage = this.mNciTransportManager.sendVendorNciMessage(GetSwpStatusCommand.create((byte) i));
        Log.d("NfcTestManager", "INDEX_SWP_STATUS = " + ((int) bArrSendVendorNciMessage[2]));
        return bArrSendVendorNciMessage[2] == 0 ? 1 : 0;
    }

    public void startPrbs(int i, int i2) {
        Log.d("NfcTestManager", "Start PRBS mode");
        this.mPrbsTech = getTech(i);
        this.mPrbsRate = getRate(i2);
        this.mSkipEnableAfterPrbs = false;
        NfcAdapter nfcAdapter = this.mNfcAdapter;
        if (nfcAdapter != null) {
            if (nfcAdapter.isEnabled()) {
                this.mIsPrbsStarted = true;
                this.mNfcAdapter.disable(false);
            } else {
                this.mSkipEnableAfterPrbs = true;
                startPrbs();
            }
        }
    }

    public void stopPrbs() {
        Log.d("NfcTestManager", "Stop PRBS mode");
        this.mNciTransportManager.sendVendorNciMessage(PrbsCommand.create((byte) 0, (byte) 1, (byte) 1));
        this.mNfcOemExtension.setControllerAlwaysOnMode(0);
    }

    public byte[] getResonantFrequencyFromClf() {
        return this.mNciTransportManager.sendVendorNciMessage(GetResoFreqCommand.create());
    }

    public boolean isPollingSkipRequired() {
        return isFactoryTestAppRunning(this.mContext) || isDiscoverOff();
    }

    public void onBootFinished() {
        disableReaderModeIfNeeded();
    }

    public void onEnableFinished() {
        disableReaderModeIfNeeded();
    }

    public static String getNfcTestRequestActionExtraIdString(int i) {
        if (i == 11) {
            return "START_READER_MODE_TEST";
        }
        if (i != 12) {
            switch (i) {
                case 0:
                    return "START_NFC_TEST";
                case 1:
                    return "STOP_NFC_TEST";
                case 2:
                    return "ENABLE_DISCOVERY";
                case 3:
                    return "DISABLE_DISCOVERY";
                case 4:
                    return "DISABLE_DISCOVERY_AFTER_TURN_ON_NFC";
                case 5:
                    return "CHECK_SIM";
                case 6:
                    return "CHECK_ESE";
                case 7:
                    return "CHECK_CARD_MODE_STATE";
                case 8:
                    return "CHECK_RESONANT_FREQUENCY";
                case 9:
                    return "CHECK_FIRMWARE_VERSION";
                default:
                    switch (i) {
                        case 21:
                            return "INDICATION_V1";
                        case 22:
                            return "INDICATION_V2";
                        case 23:
                            return "INDICATION_V3";
                        default:
                            switch (i) {
                                case 31:
                                    return "START_PRBS_TEST";
                                case 32:
                                    return "STOP_PRBS_TEST";
                                case 33:
                                    return "FORCE_FIRMWARE_DOWNLOAD";
                                case 34:
                                    return "SET_TECH_MASK";
                                default:
                                    return "default";
                            }
                    }
            }
        }
        return "STOP_READER_MODE_TEST";
    }
}
