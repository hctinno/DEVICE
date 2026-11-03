package com.samsung.android.uwb_extension.rfTest;

import android.content.Context;
import android.util.Log;
import com.samsung.android.uwb_extension.IVendorExtension;
import com.samsung.android.uwb_extension.UciBuilder;
import com.samsung.android.uwb_extension.UciParser;
import com.samsung.uwb.support.util.UwbUtil;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/* JADX INFO: loaded from: classes.dex */
public class SamsungUwbTestManager {
    private static final String TAG = SamsungUwbTestManager.class.getSimpleName();
    public static final byte UWB_LOOPBACK_TEST_MODE = 2;
    public static final byte UWB_PERIODIC_TX_TEST_MODE = 0;
    public static final byte UWB_PER_RX_TEST_MODE = 1;
    public static final byte UWB_RX_TEST_MODE = 3;
    private final IVendorExtension mIVendorExtension;
    private final UwbTestNotificationHandler mNotificationHandler;
    private Object mTestModeSessionObject;
    private int mTestModeSessionStatus = 1;

    public SamsungUwbTestManager(Context context, IVendorExtension iVendorExtension) {
        this.mIVendorExtension = iVendorExtension;
        this.mNotificationHandler = new UwbTestNotificationHandler(context);
    }

    public void onSessionStatusNotificationReceived(int sessionId, int status, int reasonCode) {
        Object obj;
        Log.d(TAG, "onSessionStatusNotificationReceived: sessionId=" + sessionId + ", status=" + status + ", reasonCode=" + reasonCode);
        if (sessionId == 0 && (obj = this.mTestModeSessionObject) != null) {
            synchronized (obj) {
                this.mTestModeSessionStatus = status;
                this.mTestModeSessionObject.notify();
            }
        }
    }

    public int openTestModeSession(final HashMap<String, ByteBuffer> params) {
        Log.d(TAG, "openTestModeSession");
        this.mTestModeSessionObject = new Object();
        ExecutorService executor = Executors.newSingleThreadExecutor();
        FutureTask<Integer> openTestModeSessionTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.rfTest.SamsungUwbTestManager$$ExternalSyntheticLambda0
            @Override // java.util.concurrent.Callable
            public final Object call() {
                return this.f$0.m187x80c398d6(params);
            }
        });
        executor.submit(openTestModeSessionTask);
        try {
            int status = openTestModeSessionTask.get(4000L, TimeUnit.MILLISECONDS).intValue();
            return status;
        } catch (InterruptedException e) {
            e.printStackTrace();
            return 2;
        } catch (ExecutionException e2) {
            e2.printStackTrace();
            return 2;
        } catch (TimeoutException e3) {
            executor.shutdownNow();
            Log.e(TAG, "openTestModeSession: Timeout occurred");
            return 2;
        }
    }

    /* JADX INFO: renamed from: lambda$openTestModeSession$0$com-samsung-android-uwb_extension-rfTest-SamsungUwbTestManager, reason: not valid java name */
    /* synthetic */ Integer m187x80c398d6(HashMap params) throws Exception {
        synchronized (this.mTestModeSessionObject) {
            byte[] uci = UciBuilder.buildSessionInit(0, (byte) -48);
            byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(1, 0, uci);
            if (respUci != null && respUci.length != 0) {
                int status = respUci[0];
                if (status != 0) {
                    return Integer.valueOf(status);
                }
                this.mTestModeSessionObject.wait();
                if (this.mTestModeSessionStatus == 0) {
                    byte[] uci2 = UciBuilder.buildSetAppConfig(0, UciBuilder.getTlvArray(params));
                    byte[] respUci2 = this.mIVendorExtension.sendVendorUciMessage(1, 3, uci2);
                    if (respUci2 != null && respUci2.length != 0) {
                        return Integer.valueOf(respUci2[0]);
                    }
                    Log.e(TAG, "openTestModeSession: respUci is null or size of respUci is zero");
                    return 2;
                }
                return 2;
            }
            Log.e(TAG, "openTestModeSession: respUci is null or size of respUci is zero");
            return 2;
        }
    }

    public int startTestModeSession(int testMode, byte[] psdu) {
        int oid;
        byte[] uci = UciBuilder.buildTestPeriodicTx(psdu);
        if (testMode == 0) {
            Log.d(TAG, "startTestModeSession: UWB_PERIODIC_TX_TEST_MODE, psdu=" + UwbUtil.toHexString(psdu));
            oid = 2;
        } else if (testMode == 1) {
            Log.d(TAG, "startTestModeSession: UWB_PER_RX_TEST_MODE, psdu=" + UwbUtil.toHexString(psdu));
            oid = 3;
        } else if (testMode == 2) {
            Log.d(TAG, "startTestModeSession: UWB_LOOPBACK_TEST_MODE, psdu=" + UwbUtil.toHexString(psdu));
            oid = 6;
        } else if (testMode == 3) {
            Log.d(TAG, "startTestModeSession: UWB_RX_TEST_MODE, psdu=" + UwbUtil.toHexString(psdu));
            oid = 5;
        } else {
            Log.e(TAG, "startTestModeSession: Unknown RF Test");
            return 2;
        }
        byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(13, oid, uci);
        if (respUci == null || respUci.length == 0) {
            Log.e(TAG, "startTestModeSession: respUci is null or size of respUci is zero");
            return 2;
        }
        int status = respUci[0];
        return status;
    }

    public int stopTestModeSession() {
        String str = TAG;
        Log.d(str, "stopTestModeSession");
        if (this.mTestModeSessionStatus == 1) {
            Log.e(str, "stopTestModeSession:Session is not initialized:");
            return 2;
        }
        byte[] uci = UciBuilder.buildTestStopSession();
        byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(13, 7, uci);
        if (respUci == null || respUci.length == 0) {
            Log.e(str, "stopTestModeSession: respUci is null or size of respUci is zero");
            return 2;
        }
        int status = respUci[0];
        return status;
    }

    public int closeTestModeSession() {
        String str = TAG;
        Log.d(str, "closeTestModeSession");
        if (this.mTestModeSessionStatus == 1) {
            Log.e(str, "closeTestModeSession:Session is not initialized:");
            return 2;
        }
        byte[] uci = UciBuilder.buildSessionDeInit(0);
        byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(1, 1, uci);
        if (respUci == null || respUci.length == 0) {
            Log.e(str, "closeTestModeSession: respUci is null or size of respUci is zero");
            return 2;
        }
        int status = respUci[0];
        return status;
    }

    public int reConfigureTestModeSession(HashMap<String, ByteBuffer> params) {
        String str = TAG;
        Log.d(str, "reConfigureTestModeSession");
        byte[] uci = UciBuilder.buildSetAppConfig(0, UciBuilder.getTlvArray(params));
        byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(13, 0, uci);
        if (respUci == null || respUci.length == 0) {
            Log.e(str, "reConfigureTestModeSession: respUci is null or size of respUci is zero");
            return 2;
        }
        int status = respUci[0];
        return status;
    }

    public HashMap<String, ByteBuffer> getTestModeSessionConfigurations(List<String> testConfigParamList) {
        String str = TAG;
        Log.d(str, "getTestModeSessionConfigurations");
        byte[] uci = UciBuilder.buildGetAppConfig(0, UciBuilder.getTagIdArray(testConfigParamList));
        byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(13, 1, uci);
        if (respUci == null || respUci.length == 0) {
            Log.e(str, "reConfigureTestModeSession: respUci is null or size of respUci is zero");
            return null;
        }
        int status = respUci[0];
        if (status != 0) {
            return null;
        }
        HashMap<String, ByteBuffer> configMap = UciParser.parseTestConfigGet(respUci);
        return configMap;
    }

    public void uciHandleRfTestNotification(int gid, int oid, byte[] data) {
        this.mNotificationHandler.uciHandleRfTestNotification(gid, oid, data);
    }

    public void registerRfTestCallback(ITestModeSessionCallback callback, Executor executor) {
        this.mNotificationHandler.registerRfTestCallback(callback, executor);
    }

    public void unregisterRfTestCallback(ITestModeSessionCallback callback) {
        this.mNotificationHandler.unregisterRfTestCallback(callback);
    }
}
