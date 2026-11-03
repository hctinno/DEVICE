package com.samsung.android.uwb_extension.factory;

import android.content.Context;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.Message;
import android.util.Log;
import com.android.internal.util.HexDump;
import com.samsung.android.scpmlib_v1.BuildConfig;
import com.samsung.android.uwb.advertisement.UwbAdvertisePostProcessor;
import com.samsung.android.uwb.data.UwbUciConstants;
import com.samsung.android.uwb_extension.IVendorExtension;
import com.samsung.android.uwb_extension.SamsungCalibrationData;
import com.samsung.android.uwb_extension.UciBuilder;
import com.samsung.android.uwb_extension.UciParser;
import com.samsung.android.uwb_extension.rfTest.ITestModeSessionCallback;
import com.samsung.android.uwb_extension.rfTest.SamsungUwbTestManager;
import com.samsung.android.uwb_extension.vendor.AbstractVendor;
import com.samsung.android.uwb_extension.vendor.factory.CalibrationResult;
import com.samsung.android.uwb_extension.vendor.factory.SeBindingCount;
import com.samsung.android.uwb_extension.vendor.factory.SeBindingResult;
import com.samsung.android.uwb_extension.vendor.factory.SeBindingStatus;
import com.samsung.android.uwb_extension.vendor.factory.SeCommmunicationResult;
import com.samsung.android.uwb_extension.vendor.factory.SeConnectivityTestResult;
import com.samsung.android.uwb_extension.vendor.factory.SeLoopbackTestResult;
import com.samsung.android.uwb_extension.vendor.factory.TestPeriodicTxResult;
import com.samsung.android.uwb_extension.vendor.factory.TestRfLoopbackResult;
import com.samsung.android.uwb_extension.vendor.factory.TestRxPacketErrorRateResult;
import com.samsung.android.uwb_extension.vendornxp.proprierity.NxpUwbDebugConfigInfo;
import com.samsung.android.uwb_extras.AppConfigExtParameters;
import com.samsung.android.uwb_extras.AppConfigParameters;
import com.samsung.android.uwb_extras.TestConfigParameters;
import com.samsung.android.uwb_extras.UwbExtrasAdapter;
import com.samsung.uwb.support.util.UwbUtil;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import kotlin.UShort;
import kotlin.jvm.internal.ByteCompanionObject;
import samsung.uwb.RangingData;
import samsung.uwb.UwbAdapter;
import samsung.uwb.UwbCallback;

/* JADX INFO: loaded from: classes.dex */
public class UwbFactoryManager implements IUwbFactoryManager, ITestModeSessionCallback {
    private static final String TAG = UwbFactoryManager.class.getSimpleName();
    private Object mEseConnectivityTestObject;
    private Object mEseDoBindObject;
    private Object mEseGetBindingStatusObject;
    private Object mEseLoopbackTestObject;
    private final Handler mHandler;
    private final HandlerThread mHandlerThread;
    private final IVendorExtension mIVendorExtension;
    private boolean mIsBindingCountChecked = false;
    private boolean mIsClkSwitchingSuccess = false;
    private Object mLockObjForClkSwitchingTest;
    private final Looper mLooper;
    private final SamsungUwbTestManager mSamsungUwbTestManager;
    private SeBindingResult mSeBindingResult;
    private SeBindingStatus mSeBindingStatus;
    private SeConnectivityTestResult mSeConnectivityTestResult;
    private SeLoopbackTestResult mSeLoopbackTestResult;
    private Object mTestLoopbackObject;
    private Object mTestPerRxObject;
    private TestRfLoopbackResult mTestRfLoopbackResult;
    private TestRxPacketErrorRateResult mTestRxPacketErrorRateResult;
    private final UwbAdapter mUwbAdapter;
    private final UwbExtrasAdapter mUwbExtrasAdapter;
    private final UwbFactoryIntentManager mUwbFactoryIntentManager;
    private final AbstractVendor mVendor;

    public UwbFactoryManager(Context context, SamsungUwbTestManager samsungUwbTestManager, AbstractVendor vendor, IVendorExtension iVendorExtension) {
        Log.d(TAG, "UwbFactoryManager is started");
        this.mSamsungUwbTestManager = samsungUwbTestManager;
        samsungUwbTestManager.registerRfTestCallback(this, Executors.newSingleThreadExecutor());
        this.mVendor = vendor;
        this.mIVendorExtension = iVendorExtension;
        this.mUwbAdapter = UwbAdapter.getUwbAdapter(context);
        this.mUwbExtrasAdapter = UwbExtrasAdapter.getUwbAdapter(context);
        HandlerThread handlerThread = new HandlerThread("UwbFactoryHandler", 10);
        this.mHandlerThread = handlerThread;
        handlerThread.start();
        Looper looper = handlerThread.getLooper();
        this.mLooper = looper;
        this.mHandler = new UwbFactoryHandler(looper);
        this.mUwbFactoryIntentManager = new UwbFactoryIntentManager(context, this);
    }

    @Override // com.samsung.android.uwb_extension.factory.IUwbFactoryManager
    public void sendMessage(int what) {
        Message msg = this.mHandler.obtainMessage();
        msg.what = what;
        this.mHandler.sendMessage(msg);
    }

    @Override // com.samsung.android.uwb_extension.factory.IUwbFactoryManager
    public void sendMessage(int what, Object obj) {
        Message msg = this.mHandler.obtainMessage();
        msg.what = what;
        msg.obj = obj;
        this.mHandler.sendMessage(msg);
    }

    @Override // com.samsung.android.uwb_extension.factory.IUwbFactoryManager
    public void sendMessage(int what, int arg1, int arg2) {
        Message msg = this.mHandler.obtainMessage();
        msg.what = what;
        msg.arg1 = arg1;
        msg.arg2 = arg2;
        this.mHandler.sendMessage(msg);
    }

    @Override // com.samsung.android.uwb_extension.factory.IUwbFactoryManager
    public void sendMessage(int what, Object obj, int arg1, int arg2) {
        Message msg = this.mHandler.obtainMessage();
        msg.what = what;
        msg.obj = obj;
        msg.arg1 = arg1;
        msg.arg2 = arg2;
        this.mHandler.sendMessage(msg);
    }

    public void onDoBindStatusNotificationReceived(SeBindingResult seBindingResult) {
        this.mSeBindingResult = seBindingResult;
        Object obj = this.mEseDoBindObject;
        if (obj != null) {
            synchronized (obj) {
                this.mEseDoBindObject.notify();
            }
        }
    }

    public void onGetBindingStatusNotificationReceived(SeBindingStatus seBindingStatus) {
        this.mSeBindingStatus = seBindingStatus;
        Object obj = this.mEseGetBindingStatusObject;
        if (obj != null) {
            synchronized (obj) {
                this.mEseGetBindingStatusObject.notify();
            }
        }
    }

    public void onDoConnectivityTestStatusNotificationReceived(SeConnectivityTestResult seConnectivityTestResult) {
        this.mSeConnectivityTestResult = seConnectivityTestResult;
        Object obj = this.mEseConnectivityTestObject;
        if (obj != null) {
            synchronized (obj) {
                this.mEseConnectivityTestObject.notify();
            }
        }
    }

    public void onDoLoopTestStatusNotificationReceived(SeLoopbackTestResult seLoopbackTestResult) {
        this.mSeLoopbackTestResult = seLoopbackTestResult;
        Object obj = this.mEseLoopbackTestObject;
        if (obj != null) {
            synchronized (obj) {
                this.mEseLoopbackTestObject.notify();
            }
        }
    }

    public void onSeCommStatusNotificationReceived(SeCommmunicationResult seCommunicationStatus) {
        Log.d(TAG, "onSeCommStatusNotificationReceived");
    }

    @Override // com.samsung.android.uwb_extension.rfTest.ITestModeSessionCallback
    public void onTestPeriodicTxDataNotificationReceived(TestPeriodicTxResult testPeriodicTxResult) {
        Log.d(TAG, "onTestPeriodicTxDataNotificationReceived");
    }

    @Override // com.samsung.android.uwb_extension.rfTest.ITestModeSessionCallback
    public void onTestPerRxDataNotificationReceived(TestRxPacketErrorRateResult testRxPacketErrorRateResult) {
        Log.d(TAG, "onTestPerRxDataNotificationReceived: " + testRxPacketErrorRateResult);
        this.mTestRxPacketErrorRateResult = testRxPacketErrorRateResult;
        Object obj = this.mTestPerRxObject;
        if (obj != null) {
            synchronized (obj) {
                this.mTestPerRxObject.notify();
            }
        }
    }

    @Override // com.samsung.android.uwb_extension.rfTest.ITestModeSessionCallback
    public void onTestRxDataNotificationReceived() {
        Log.d(TAG, "onTestRxDataNotificationReceived");
    }

    @Override // com.samsung.android.uwb_extension.rfTest.ITestModeSessionCallback
    public void onTestLoopbackDataNotificationReceived(TestRfLoopbackResult testRfLoopbackResults) {
        Log.d(TAG, "onTestLoopbackDataNotificationReceived: " + testRfLoopbackResults);
        this.mTestRfLoopbackResult = testRfLoopbackResults;
        Object obj = this.mTestLoopbackObject;
        if (obj != null) {
            synchronized (obj) {
                this.mTestLoopbackObject.notify();
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    final class UwbFactoryHandler extends Handler {
        private List<Float> mAoaArr;
        private byte mCurrentChannel;
        private int mCurrentRangingCount;
        private byte mCurrentRxAntenna;
        private int mCurrentSessionId;
        private byte mCurrentTxAntenna;
        private short mDeviceMacAddress;
        private short mDstMacAddress;
        private int mFilterCount;
        private boolean mIsEnabled;
        private boolean mIsUwbRangingOn;
        private int mMaxRangingCount;
        private List<Float> mPdoaArr;
        private int mPerRxTimeout;

        public UwbFactoryHandler(Looper looper) {
            super(looper);
            this.mIsEnabled = false;
            this.mCurrentSessionId = 0;
            this.mCurrentTxAntenna = (byte) 1;
            this.mCurrentRxAntenna = (byte) 1;
            this.mCurrentChannel = (byte) 9;
            this.mPerRxTimeout = UwbAdvertisePostProcessor.TIME_THRESHOLD;
            this.mIsUwbRangingOn = false;
            this.mDeviceMacAddress = (short) 0;
            this.mDstMacAddress = (short) 1;
            this.mMaxRangingCount = 100;
            this.mCurrentRangingCount = 0;
            this.mFilterCount = 0;
            this.mPdoaArr = new ArrayList();
            this.mAoaArr = new ArrayList();
        }

        /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
        /* JADX WARN: Code duplicated, block: B:162:0x0708  */
        /* JADX WARN: Code duplicated, block: B:266:0x0b72  */
        /* JADX WARN: Code duplicated, block: B:426:0x122c  */
        /* JADX WARN: Code duplicated, block: B:473:0x1359  */
        /* JADX WARN: Code duplicated, block: B:694:0x1d4a  */
        /* JADX WARN: Code duplicated, block: B:695:0x1d54  */
        /* JADX WARN: Multi-variable type inference failed */
        @Override // android.os.Handler
        public void handleMessage(Message msg) throws IOException {
            byte tx;
            byte[] rxAntPairs;
            byte tx2;
            byte rx;
            String path;
            byte[] rxAntPairs2;
            String path2;
            int rxAntPairs3;
            int rxAntPairs4;
            String path3;
            int rxAntPairs5;
            byte tx3;
            SamsungCalibrationData.RxAntennaConfiguration rxAntConfig;
            int rxAntPairs6;
            byte tx4;
            byte tx5;
            byte rxAntMode;
            byte[] rxAntPairs7;
            byte rxAntId;
            String str;
            char c;
            int i;
            byte rxAntId2;
            int msgType = msg.what;
            String str2 = UwbFactoryIntentManager.DATA_OK;
            switch (msgType) {
                case 0:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_UWB_OFF");
                    this.mIsUwbRangingOn = false;
                    int res = UwbFactoryManager.this.mUwbAdapter.disable();
                    if (res == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        this.mIsEnabled = false;
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 1:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_UWB_ON");
                    if (true == this.mIsEnabled) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                    int res2 = UwbFactoryManager.this.mUwbAdapter.enable();
                    if (res2 == 0) {
                        this.mIsEnabled = true;
                        this.mCurrentSessionId = 0;
                        int res3 = UwbFactoryManager.this.mSamsungUwbTestManager.openTestModeSession(new AppConfigParameters.Builder().setStsConfig((byte) 0).setChannelNumber((byte) 9).setNoOfControlee((byte) 1).setDeviceMacAddress((short) 0).setDstMacAddress((short) 1).setMacFcsType((byte) 0).setRframeConfig((byte) 3).setPreambleCodeIndex((byte) 9).setSfdId((byte) 0).setPsduDataRate((byte) 0).setPreambleDuration((byte) 1).setTxAdaptivePayloadPower((byte) 0).setPrfMode((byte) 0).setMacAddressMode((byte) 0).setNoOfStsSegments((byte) 1).build().getConfigMap());
                        if (res3 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_UWB_ON: openTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res4 = UwbFactoryManager.this.mSamsungUwbTestManager.reConfigureTestModeSession(new TestConfigParameters.Builder().setNumOfPkts(1000).setTGap(2000).setTStart(UwbFactoryConstant.T_START_450).setTWin(UwbFactoryConstant.T_WIN_750).setRandomPsduSize((byte) 0).setPhrRangingBit((byte) 0).setRmarkerTxStart(0).setRmarkerRxStart(0).setStsIndexAutoInc((byte) 0).setRssiAvgFiltCnt(10).setRssiCalibrationOpt((byte) 1).setTestSessionStsKeyOpt((byte) 0).build().getConfigMap());
                        if (res4 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_UWB_ON: reConfigureTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        }
                    }
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_UWB_ON: enable Failed");
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 2:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL");
                    int pllCalCh5 = -1;
                    int pllCalCh9 = -1;
                    boolean pllCal5Status = false;
                    boolean pllCal9Status = false;
                    boolean dcdcStatus = false;
                    CalibrationResult res5 = UwbFactoryManager.this.mVendor.doCalibration((byte) 5, (byte) 0);
                    if (res5.getStatus() == 0) {
                        byte[] bytePllCalCh5 = res5.getValue();
                        pllCalCh5 = ((bytePllCalCh5[1] & 63) << 8) + (bytePllCalCh5[0] & 255);
                        pllCal5Status = (bytePllCalCh5[1] & ByteCompanionObject.MIN_VALUE) == -128;
                        dcdcStatus = (bytePllCalCh5[1] & 64) != 64;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: CH5 Failed");
                    }
                    CalibrationResult res6 = UwbFactoryManager.this.mVendor.doCalibration((byte) 9, (byte) 0);
                    if (res6.getStatus() == 0) {
                        byte[] bytePllCalCh9 = res6.getValue();
                        pllCalCh9 = ((bytePllCalCh9[1] & 63) << 8) + (bytePllCalCh9[0] & 255);
                        pllCal9Status = (bytePllCalCh9[1] & ByteCompanionObject.MIN_VALUE) == -128;
                        dcdcStatus &= (bytePllCalCh9[1] & 64) != 64;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: CH9 Failed");
                    }
                    if (pllCalCh5 == -1 || pllCalCh9 == -1) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: VCO PLL Cal not working");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + pllCalCh5 + "," + pllCalCh9 + ",-1");
                        return;
                    }
                    if (!pllCal5Status || !pllCal9Status) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: VCO PLL locking failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + pllCalCh5 + "," + pllCalCh9 + ",0");
                        return;
                    }
                    if (!dcdcStatus) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: DCDC screening value is invalid");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + pllCalCh5 + "," + pllCalCh9 + ",-6");
                        return;
                    }
                    if (pllCalCh5 < 0 || pllCalCh5 > 511 || pllCalCh9 < 0 || pllCalCh9 > 511) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: VCO PLL value is out of range (Ch5=" + pllCalCh5 + ",Ch9=" + pllCalCh9 + ")");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + pllCalCh5 + "," + pllCalCh9 + ",1");
                        return;
                    } else if (!UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH5_VCO_PLL_CAL, Integer.valueOf(pllCalCh5)) || !UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH9_VCO_PLL_CAL, Integer.valueOf(pllCalCh9))) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: Write VCO PLL code into EFS failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + pllCalCh5 + "," + pllCalCh9 + ",-5");
                        return;
                    } else {
                        Log.d(UwbFactoryManager.TAG, "MSG_TEST_CAL_RF_PLL: VCO PLL Cal success");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + pllCalCh5 + "," + pllCalCh9);
                        return;
                    }
                case 3:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_RANGING_OFF");
                    int res7 = UwbFactoryManager.this.mUwbAdapter.disable();
                    if (res7 == 0) {
                        this.mIsUwbRangingOn = false;
                        this.mIsEnabled = false;
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 4:
                    int sessionId = ((Integer) msg.obj).intValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_RANGING_ON: sessionId=" + sessionId);
                    if (this.mIsUwbRangingOn) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                    int res8 = UwbFactoryManager.this.mUwbAdapter.enable();
                    if (res8 == 0) {
                        int res9 = UwbFactoryManager.this.mUwbAdapter.openSession(sessionId, 1000, true, new UwbCallback() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager.UwbFactoryHandler.1
                            public void onRangingDataReceived(RangingData rangingData) {
                                if (rangingData == null) {
                                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START: RangingData is null");
                                    return;
                                }
                                if (UwbFactoryHandler.this.mCurrentRangingCount > UwbFactoryHandler.this.mMaxRangingCount) {
                                    return;
                                }
                                if (UwbFactoryHandler.this.mCurrentRangingCount == UwbFactoryHandler.this.mMaxRangingCount) {
                                    int result = UwbFactoryManager.this.mUwbAdapter.rangingStop(UwbFactoryHandler.this.mCurrentSessionId);
                                    if (result != 0) {
                                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START: Ranging Stop Failed, result=" + result);
                                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                        return;
                                    }
                                    int validCnt = UwbFactoryHandler.this.mPdoaArr.size() - (UwbFactoryHandler.this.mFilterCount * 2);
                                    if (validCnt <= 0) {
                                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                        return;
                                    }
                                    UwbFactoryHandler.this.mPdoaArr.sort(null);
                                    for (int i2 = 0; i2 < UwbFactoryHandler.this.mFilterCount; i2++) {
                                        UwbFactoryHandler.this.mPdoaArr.remove(0);
                                        UwbFactoryHandler.this.mPdoaArr.remove(UwbFactoryHandler.this.mPdoaArr.size() - 1);
                                    }
                                    UwbFactoryHandler.this.mAoaArr.sort(null);
                                    for (int i3 = 0; i3 < UwbFactoryHandler.this.mFilterCount; i3++) {
                                        UwbFactoryHandler.this.mAoaArr.remove(0);
                                        UwbFactoryHandler.this.mAoaArr.remove(UwbFactoryHandler.this.mAoaArr.size() - 1);
                                    }
                                    float sumOfPdoa = 0.0f;
                                    float sumOfAoa = 0.0f;
                                    for (int i4 = 0; i4 < UwbFactoryHandler.this.mPdoaArr.size(); i4++) {
                                        sumOfPdoa += ((Float) UwbFactoryHandler.this.mPdoaArr.get(i4)).floatValue();
                                        sumOfAoa += ((Float) UwbFactoryHandler.this.mAoaArr.get(i4)).floatValue();
                                    }
                                    float pdoaAverage = UwbUtil.floor(sumOfPdoa / validCnt, 2);
                                    float aoaAverage = UwbUtil.floor(sumOfAoa / validCnt, 2);
                                    Log.d(UwbFactoryManager.TAG, "rangingCount=" + UwbFactoryHandler.this.mCurrentRangingCount + ", outlierCount=" + UwbFactoryHandler.this.mFilterCount + ", validCnt=" + validCnt);
                                    Log.d(UwbFactoryManager.TAG, "pdoaSum=" + sumOfPdoa + ", aoaSum=" + sumOfAoa + " / pdoaAvg=" + pdoaAverage + ", aoaAvg=" + aoaAverage);
                                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(String.format(Locale.US, "%.2f, %.2f", Float.valueOf(pdoaAverage), Float.valueOf(aoaAverage)));
                                }
                                UwbFactoryHandler.this.mCurrentRangingCount++;
                                if (rangingData.getRangingMeasures()[0].getRangingStatus() == 0) {
                                    float pdoa = UwbUtil.floor(rangingData.getRangingMeasures()[0].getPDoAFirst(), 2);
                                    float aoa = UwbUtil.floor(rangingData.getRangingMeasures()[0].getAoAFirst(), 2);
                                    UwbFactoryHandler.this.mPdoaArr.add(Float.valueOf(pdoa));
                                    UwbFactoryHandler.this.mAoaArr.add(Float.valueOf(aoa));
                                    Log.d(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START: onRangingDataReceived[PDoA=" + pdoa + ", AoA=" + aoa + "]");
                                }
                            }

                            public void onSessionStatusChanged(int status, int reasonCode) {
                            }
                        });
                        if (res9 != 0) {
                            this.mIsUwbRangingOn = false;
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        } else {
                            this.mIsUwbRangingOn = true;
                            this.mCurrentSessionId = sessionId;
                        }
                        try {
                            Thread.sleep(300L);
                            break;
                        } catch (InterruptedException e) {
                        }
                        int res10 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setDeviceRole((byte) 0).setDeviceType((byte) 0).setMultiNodeMode((byte) 0).setNoOfControlee((byte) 1).setDstMacAddress(UwbUtil.getByteArray((short) 11)).setDeviceMacAddress(UwbUtil.getByteArray((short) 1)).setChannelNumber((byte) 9).setSlotDuration((short) 2400).setSlotsPerRangingRound((byte) 10).setPreambleCodeIndex((byte) 10).setRangingRoundControl((byte) 3).setRangingDataNtf((byte) 1).setRangingRoundUsage((byte) 2).setRangingInterval(40).setNoOfStsSegments((byte) 1).setRframeConfig((byte) 3).setStsConfig((byte) 0).setStsIndex(1000).setSfdId((byte) 0).build());
                        if (res10 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RANGING_ON: setAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res11 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setMacPayloadEncryption((byte) 2).build());
                        if (res11 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START: setExtAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        } else {
                            this.mDeviceMacAddress = (short) 1;
                            this.mDstMacAddress = (short) 11;
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        }
                    }
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 5:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_CREATE_AOA_CAL_TO_EFS");
                    boolean result = UwbFactoryConstant.copyFile(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE, UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS);
                    UwbFactoryIntentManager uwbFactoryIntentManager = UwbFactoryManager.this.mUwbFactoryIntentManager;
                    if (!result) {
                        str2 = UwbFactoryIntentManager.DATA_NG;
                    }
                    uwbFactoryIntentManager.sendResponse(str2);
                    return;
                case 6:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_COMPARE_AOA_CAL");
                    String versionConf = SamsungCalibrationData.readCalibrationFileVersion(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE);
                    if (!UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS)) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + versionConf + "," + UwbFactoryIntentManager.DATA_NONE);
                        return;
                    }
                    String versionEfs = SamsungCalibrationData.readCalibrationFileVersion(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS);
                    if (UwbFactoryConstant.isFileEquals(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE, UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS) && versionConf.length() == 4) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + versionConf + "," + versionEfs);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + versionConf + "," + versionEfs);
                        return;
                    }
                case 7:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_COMPARE_AOA_CAL_VERSION");
                    String versionConf2 = SamsungCalibrationData.readCalibrationFileVersion(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE);
                    if (!UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS)) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + versionConf2 + "," + UwbFactoryIntentManager.DATA_NONE);
                        return;
                    }
                    String versionEfs2 = SamsungCalibrationData.readCalibrationFileVersion(UwbFactoryConstant.PATH_CALIBRATION_CONFIG_FILE_IN_EFS);
                    if (!versionConf2.equals(UwbFactoryIntentManager.DATA_NG) && !versionEfs2.equals(UwbFactoryIntentManager.DATA_NG)) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + versionConf2 + "," + versionEfs2);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG," + versionConf2 + "," + versionEfs2);
                        return;
                    }
                case 8:
                    String txAnt = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA: txAnt=" + txAnt);
                    if (txAnt.equals(UwbFactoryConstant.TX_ANT_0)) {
                        tx = 1;
                    } else if (txAnt.equals(UwbFactoryConstant.TX_ANT_1)) {
                        tx = 2;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA: Undefined Tx ANT");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res12 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigTx(tx, (byte) 0).build());
                    if (res12 == 0) {
                        this.mCurrentTxAntenna = tx;
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA: setExtAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 9:
                    String rxAnt = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA: rxAnt=" + rxAnt);
                    byte[] bArr = new byte[1];
                    if (rxAnt.equals(UwbFactoryConstant.RX_ANT_0)) {
                        rxAntPairs = new byte[]{1};
                        this.mCurrentRxAntenna = (byte) 1;
                    } else if (rxAnt.equals(UwbFactoryConstant.RX_ANT_1)) {
                        rxAntPairs = new byte[]{2};
                        this.mCurrentRxAntenna = (byte) 2;
                    } else if (rxAnt.equals(UwbFactoryConstant.RX_ANT_2)) {
                        rxAntPairs = new byte[]{3};
                        this.mCurrentRxAntenna = (byte) 3;
                    } else if (rxAnt.equals(UwbFactoryConstant.RX_ANT_3)) {
                        rxAntPairs = new byte[]{4};
                        this.mCurrentRxAntenna = (byte) 4;
                    } else if (rxAnt.equals(UwbFactoryConstant.RX_ANT_4)) {
                        rxAntPairs = new byte[]{5};
                        this.mCurrentRxAntenna = (byte) 5;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA: Undefined Rx ANT");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res13 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx((byte) 1, rxAntPairs).build());
                    if (res13 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA: setExtAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 10:
                    byte channel = ((Byte) msg.obj).byteValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_CHANNEL: channel=" + ((int) channel));
                    int res14 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setChannelNumber(channel).build());
                    if (res14 == 0) {
                        this.mCurrentChannel = channel;
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_CHANNEL: setAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 11:
                    String[] sDataArray = (String[]) msg.obj;
                    try {
                        int gap = Integer.parseInt(sDataArray[0]);
                        int win = Integer.parseInt(sDataArray[1]);
                        int noOfPackets = Integer.parseInt(sDataArray[2]);
                        Log.i(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET: TGap=" + gap + ", TWin=" + win + ", noOfPackets=" + noOfPackets);
                        int res15 = UwbFactoryManager.this.mSamsungUwbTestManager.reConfigureTestModeSession(new TestConfigParameters.Builder().setTGap(gap).setTWin(win).setNumOfPkts(noOfPackets).build().getConfigMap());
                        if (res15 == 0) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET: reConfigureTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (Exception e2) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET: Exception occurred");
                        e2.printStackTrace();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 12:
                    String[] sDataArray2 = (String[]) msg.obj;
                    try {
                        int gap2 = Integer.parseInt(sDataArray2[0]);
                        int win2 = Integer.parseInt(sDataArray2[1]);
                        int noOfPackets2 = Integer.parseInt(sDataArray2[2]);
                        this.mPerRxTimeout = Integer.parseInt(sDataArray2[3]) / 1000;
                        int filterCnt = Integer.parseInt(sDataArray2[4]);
                        Log.i(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET_WITH_FILTER: TGap=" + gap2 + ", TWin=" + win2 + ", noOfPackets=" + noOfPackets2 + ", filterCnt=" + filterCnt);
                        int res16 = UwbFactoryManager.this.mSamsungUwbTestManager.reConfigureTestModeSession(new TestConfigParameters.Builder().setTGap(gap2).setTWin(win2).setNumOfPkts(noOfPackets2).setRssiAvgFiltCnt(filterCnt).build().getConfigMap());
                        if (res16 == 0) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET_WITH_FILTER: reConfigureTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (Exception e3) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_CHANGE_GAP_AND_PACKET_WITH_FILTER: Exception occurred");
                        e3.printStackTrace();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 13:
                    byte preambleIndex = ((Byte) msg.obj).byteValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_PREAMBLE_INDEX: preambleCode=" + ((int) preambleIndex));
                    int res17 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setPreambleCodeIndex(preambleIndex).build());
                    if (res17 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_PREAMBLE_INDEX: setAppConfigurations Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 14:
                    String[] sDataArray3 = (String[]) msg.obj;
                    short rangingInterval = 40;
                    try {
                        int rangingCount = Integer.parseInt(sDataArray3[0]);
                        int filterCount = Integer.parseInt(sDataArray3[1]);
                        short deviceMacAddress = Short.parseShort(sDataArray3[2]);
                        short dstMacAddress = Short.parseShort(sDataArray3[3]);
                        int stsIndex = Integer.parseInt(sDataArray3[4]);
                        if (sDataArray3.length == 6) {
                            rangingInterval = Short.parseShort(sDataArray3[5]);
                        }
                        Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_AOA_RANGING_CONFIG: RangingCount=" + rangingCount + ", FilterCount=" + filterCount + ", DeviceMacAddress=" + ((int) deviceMacAddress) + ", DstMacAddress=" + ((int) dstMacAddress) + ", StsIndex=" + stsIndex + ", RangingInterval=" + ((int) rangingInterval));
                        int res18 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setDstMacAddress(UwbUtil.getByteArray(dstMacAddress)).setDeviceMacAddress(UwbUtil.getByteArray(deviceMacAddress)).setStsIndex(stsIndex).setRangingInterval(rangingInterval).build());
                        if (res18 == 0) {
                            this.mDeviceMacAddress = deviceMacAddress;
                            this.mDstMacAddress = dstMacAddress;
                            this.mMaxRangingCount = rangingCount;
                            this.mFilterCount = filterCount;
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        }
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_AOA_RANGING_CONFIG: setAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } catch (Exception e4) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_AOA_RANGING_CONFIG: Exception occurred");
                        e4.printStackTrace();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 15:
                    byte rframeConfig = ((Byte) msg.obj).byteValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_STS_PACKET_TYPE: rframeConfig=" + ((int) rframeConfig));
                    byte numOfSegment = 1;
                    if (rframeConfig == 0) {
                        numOfSegment = 0;
                    }
                    int res19 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setRframeConfig(rframeConfig).setNoOfStsSegments(numOfSegment).build());
                    if (res19 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_STS_PACKET_TYPE: setAppConfigurations Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 16:
                    byte antennaPair = ((Byte) msg.obj).byteValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: antennaPair=" + ((int) antennaPair));
                    int res20 = UwbFactoryManager.this.mUwbAdapter.enable();
                    if (res20 == 0) {
                        this.mCurrentSessionId = 0;
                        short deviceMacAddress2 = 0;
                        int res21 = UwbFactoryManager.this.mSamsungUwbTestManager.openTestModeSession(new AppConfigParameters.Builder().setStsConfig((byte) 0).setChannelNumber((byte) 9).setNoOfControlee((byte) 1).setDeviceMacAddress((short) 0).setDstMacAddress((short) 0).setMacFcsType((byte) 0).setRframeConfig((byte) 1).setPreambleCodeIndex((byte) 9).setSfdId((byte) 0).setPsduDataRate((byte) 0).setPreambleDuration((byte) 1).setTxAdaptivePayloadPower((byte) 0).setPrfMode((byte) 0).setMacAddressMode((byte) 0).setNoOfStsSegments((byte) 1).build().getConfigMap());
                        if (res21 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: openTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res22 = UwbFactoryManager.this.mSamsungUwbTestManager.reConfigureTestModeSession(new TestConfigParameters.Builder().setNumOfPkts(1000).setTGap(2000).setTStart(UwbFactoryConstant.T_START_450).setTWin(UwbFactoryConstant.T_WIN_750).setRandomPsduSize((byte) 0).setPhrRangingBit((byte) 0).setRmarkerTxStart(UwbFactoryConstant.RMARKER_TX_START_FOR_LOOPBACK).setRmarkerRxStart(69).setStsIndexAutoInc((byte) 1).setRssiAvgFiltCnt(10).setRssiCalibrationOpt((byte) 1).build().getConfigMap());
                        if (res22 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: reConfigureTestModeSession Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res23 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setAoaResultReq((byte) 0).build());
                        if (res23 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: setAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        byte[] txPower = {2, 1, UwbFactoryConstant.TX_POWER_ID_125, 0, 2, UwbFactoryConstant.TX_POWER_ID_125, 0};
                        CalibrationResult calResult = UwbFactoryManager.this.mVendor.setCalibration((byte) 9, UwbUciConstants.POWER_OFFSET_47_DBM, txPower);
                        if (calResult == null) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: Cal Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res24 = calResult.getStatus();
                        if (res24 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: setExtAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        if (antennaPair == 1) {
                            tx2 = 2;
                            rx = 3;
                            this.mCurrentRxAntenna = (byte) 3;
                        } else if (antennaPair == 2) {
                            tx2 = 2;
                            rx = 4;
                            this.mCurrentRxAntenna = (byte) 4;
                        } else if (antennaPair == 3) {
                            tx2 = 1;
                            rx = 3;
                            this.mCurrentRxAntenna = (byte) 3;
                        } else if (antennaPair == 4) {
                            tx2 = 1;
                            rx = 4;
                            this.mCurrentRxAntenna = (byte) 4;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: Undefined ANT Pair");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        byte[] rxAntPairs8 = {rx};
                        int res25 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx((byte) 1, rxAntPairs8).setAntennasConfigTx(tx2, (byte) 0).build());
                        if (res25 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: setExtAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int i2 = 0;
                        float maxRssi = -90.0f;
                        while (i2 < 3) {
                            int res26 = res25;
                            UwbFactoryManager.this.mTestLoopbackObject = new Object();
                            ExecutorService executor = Executors.newSingleThreadExecutor();
                            byte tx6 = tx2;
                            FutureTask<Integer> TestLoopbackTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda0
                                @Override // java.util.concurrent.Callable
                                public final Object call() {
                                    return this.f$0.m179x954ddf3c();
                                }
                            });
                            executor.submit(TestLoopbackTask);
                            byte[] txPower2 = txPower;
                            int status = 2;
                            short deviceMacAddress3 = deviceMacAddress2;
                            CalibrationResult calResult2 = calResult;
                            try {
                                status = TestLoopbackTask.get(4000, TimeUnit.MILLISECONDS).intValue();
                            } catch (InterruptedException e5) {
                                e5.printStackTrace();
                            } catch (ExecutionException e6) {
                                e6.printStackTrace();
                            } catch (TimeoutException e7) {
                                executor.shutdownNow();
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: Timeout occurred");
                            }
                            UwbFactoryManager.this.mTestLoopbackObject = null;
                            if (status != 0) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: RF Loopback Failed in repeat " + i2);
                            } else if (UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx1() != 0.0f && UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx2() != 0.0f) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: RF Loopback works with dual RX");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            } else {
                                if (UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx1() != 0.0f && maxRssi < UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx1()) {
                                    maxRssi = UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx1();
                                }
                                if (UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx2() != 0.0f && maxRssi < UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx2()) {
                                    maxRssi = UwbFactoryManager.this.mTestRfLoopbackResult.getRssiRx2();
                                }
                                Log.d(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: RF Loopback Success in repeat " + i2);
                                i2++;
                                res25 = res26;
                                tx2 = tx6;
                                txPower = txPower2;
                                deviceMacAddress2 = deviceMacAddress3;
                                calResult = calResult2;
                            }
                            if (maxRssi == -90.0f) {
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            } else {
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + String.format(Locale.US, "%.2f", Float.valueOf(maxRssi)));
                            }
                            UwbFactoryManager.this.mUwbAdapter.disable();
                            return;
                        }
                        if (maxRssi == -90.0f) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + String.format(Locale.US, "%.2f", Float.valueOf(maxRssi)));
                        }
                        UwbFactoryManager.this.mUwbAdapter.disable();
                        return;
                    }
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: enable Failed");
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 17:
                    byte txPowerId = ((Byte) msg.obj).byteValue();
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: TX powerId=" + ((int) txPowerId));
                    CalibrationResult calResult3 = UwbFactoryManager.this.mVendor.setCalibration(this.mCurrentChannel, UwbUciConstants.POWER_OFFSET_47_DBM, new byte[]{2, 1, txPowerId, 0, 2, txPowerId, 0});
                    if (calResult3 == null) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: Cal Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res27 = calResult3.getStatus();
                    if (res27 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: setExtAppConfigurations Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res28 = UwbFactoryManager.this.mSamsungUwbTestManager.startTestModeSession(0, HexDump.hexStringToByteArray(UwbFactoryConstant.PSDU));
                    if (res28 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: startTestModeSession Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                case 18:
                    byte b = this.mCurrentChannel;
                    if (b == 5) {
                        byte b2 = this.mCurrentTxAntenna;
                        if (b2 == 1) {
                            path = UwbFactoryConstant.PATH_CH5_RANGING_TX_POWER_CAL;
                        } else if (b2 == 2) {
                            path = UwbFactoryConstant.PATH_CH5_AOA_TX_POWER_CAL;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: Undefined Tx ANT");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } else if (b == 9) {
                        byte b3 = this.mCurrentTxAntenna;
                        if (b3 == 1) {
                            path = UwbFactoryConstant.PATH_CH9_RANGING_TX_POWER_CAL;
                        } else if (b3 == 2) {
                            path = UwbFactoryConstant.PATH_CH9_AOA_TX_POWER_CAL;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: Undefined Tx ANT");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: Undefined Channel");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    if (!UwbFactoryConstant.isFileExists(path)) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: Read Calibrated Tx Power Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    byte txPowerId2 = UwbFactoryConstant.readStringAsByte(path);
                    CalibrationResult calResult4 = UwbFactoryManager.this.mVendor.setCalibration(this.mCurrentChannel, UwbUciConstants.POWER_OFFSET_47_DBM, new byte[]{2, 1, txPowerId2, 0, 2, txPowerId2, 0});
                    if (calResult4 == null) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_POWER: Cal Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res29 = calResult4.getStatus();
                    if (res29 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: setExtAppConfigurations Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res30 = UwbFactoryManager.this.mSamsungUwbTestManager.startTestModeSession(0, HexDump.hexStringToByteArray(UwbFactoryConstant.PSDU));
                    if (res30 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_CALIBRATED_POWER: startTestModeSession Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                case 19:
                    String rxAntennaToRead = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI: rxAnt=" + rxAntennaToRead);
                    byte[] bArr2 = new byte[1];
                    if (rxAntennaToRead.equals(UwbFactoryConstant.RX_ANT_0)) {
                        byte[] rxAntPairs9 = {1};
                        this.mCurrentRxAntenna = (byte) 1;
                        rxAntPairs2 = rxAntPairs9;
                    } else if (rxAntennaToRead.equals(UwbFactoryConstant.RX_ANT_1)) {
                        byte[] rxAntPairs10 = {2};
                        this.mCurrentRxAntenna = (byte) 2;
                        rxAntPairs2 = rxAntPairs10;
                    } else if (rxAntennaToRead.equals(UwbFactoryConstant.RX_ANT_2)) {
                        byte[] rxAntPairs11 = {3};
                        this.mCurrentRxAntenna = (byte) 3;
                        rxAntPairs2 = rxAntPairs11;
                    } else if (rxAntennaToRead.equals(UwbFactoryConstant.RX_ANT_3)) {
                        byte[] rxAntPairs12 = {4};
                        this.mCurrentRxAntenna = (byte) 4;
                        rxAntPairs2 = rxAntPairs12;
                    } else if (rxAntennaToRead.equals(UwbFactoryConstant.RX_ANT_4)) {
                        byte[] rxAntPairs13 = {5};
                        this.mCurrentRxAntenna = (byte) 5;
                        rxAntPairs2 = rxAntPairs13;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI: Undefined Rx Ant to Read");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res31 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx((byte) 1, rxAntPairs2).build());
                    if (res31 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI: setExtAppConfigurations Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    UwbFactoryManager.this.mTestPerRxObject = new Object();
                    ExecutorService executor2 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> TestPerRxTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda1
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m180x9c76c17d();
                        }
                    });
                    executor2.submit(TestPerRxTask);
                    int timeout = this.mPerRxTimeout;
                    int status2 = 2;
                    try {
                        status2 = TestPerRxTask.get(timeout, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e8) {
                        e8.printStackTrace();
                    } catch (ExecutionException e9) {
                        e9.printStackTrace();
                    } catch (TimeoutException e10) {
                        executor2.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI: Timeout occurred");
                    }
                    UwbFactoryManager.this.mTestPerRxObject = null;
                    if (status2 != 0) {
                        UwbFactoryManager.this.mSamsungUwbTestManager.stopTestModeSession();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    float rssi = 0.0f;
                    float snr = 0.0f;
                    int len = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi().length;
                    int i3 = 0;
                    while (i3 < len) {
                        String rxAntennaToRead2 = rxAntennaToRead;
                        if (UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i3] < 0.0f && UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i3] > -90.0f) {
                            float rssi2 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i3];
                            snr = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[i3];
                            rssi = rssi2;
                        }
                        i3++;
                        rxAntennaToRead = rxAntennaToRead2;
                    }
                    String str3 = String.format(Locale.US, "%.2f,%.2f", Float.valueOf(rssi), Float.valueOf(snr));
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + (str3 + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAttempts() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAcqDetect() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAcqReject() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRxFail() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getPhrDecError() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getPsduDecError()));
                    return;
                case 20:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START");
                    this.mCurrentRangingCount = 0;
                    this.mPdoaArr.clear();
                    this.mAoaArr.clear();
                    int res32 = UwbFactoryManager.this.mUwbAdapter.rangingStart(this.mCurrentSessionId);
                    if (res32 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_RANGING_START: rangingStart Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    return;
                case 21:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_WRITE_TO_EFS");
                    String[] sData = (String[]) msg.obj;
                    String fileName = sData[0];
                    String powerIndex = sData[1];
                    FileOutputStream fileOutputStream = null;
                    try {
                        try {
                            fileOutputStream = new FileOutputStream(UwbFactoryConstant.PATH_DEFAULT + fileName);
                            fileOutputStream.write(powerIndex.getBytes(StandardCharsets.UTF_8));
                            fileOutputStream.flush();
                            fileOutputStream.getFD().sync();
                            Log.d(UwbFactoryManager.TAG, "writeToEfs path: " + fileName + ", powerIndex: " + powerIndex);
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            try {
                                fileOutputStream.close();
                                return;
                            } catch (IOException e11) {
                                Log.w(UwbFactoryManager.TAG, "writeToEfs", e11);
                                return;
                            }
                        } catch (IOException e12) {
                            Log.w(UwbFactoryManager.TAG, "writeToEfs", e12);
                            if (fileOutputStream != null) {
                                try {
                                    fileOutputStream.close();
                                } catch (IOException e13) {
                                    Log.w(UwbFactoryManager.TAG, "writeToEfs", e13);
                                }
                                break;
                            }
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (Throwable th) {
                        if (fileOutputStream != null) {
                            try {
                                fileOutputStream.close();
                                throw th;
                            } catch (IOException e14) {
                                Log.w(UwbFactoryManager.TAG, "writeToEfs", e14);
                                throw th;
                            }
                        }
                        throw th;
                    }
                case 22:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_FROM_EFS");
                    String path4 = (String) msg.obj;
                    String res33 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_DEFAULT + path4);
                    if (res33 == null) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NONE);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(res33);
                        return;
                    }
                case 23:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET");
                    String[] phaseData = (String[]) msg.obj;
                    String rxPair = phaseData[1];
                    try {
                        byte channel2 = Byte.parseByte(phaseData[0]);
                        try {
                            float phaseOffset = Float.parseFloat(phaseData[2]);
                            switch (rxPair) {
                                case "AOA_PORTRAIT":
                                    path2 = UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET;
                                    rxAntPairs3 = 1;
                                    break;
                                case "AOA_LANDSCAPE":
                                    path2 = UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET;
                                    rxAntPairs3 = 2;
                                    break;
                                case "P1:P2":
                                    path2 = UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET;
                                    rxAntPairs3 = 1;
                                    break;
                                case "P1:P3":
                                    path2 = UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET;
                                    rxAntPairs3 = 2;
                                    break;
                                default:
                                    Log.w(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET: invalid Rx Antenna Pair");
                                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                    return;
                            }
                            int result2 = 2;
                            byte[] uci = UciBuilder.buildGetPdoaOffset(channel2, NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF);
                            byte[] respUci = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 18, uci);
                            if (respUci != null && respUci.length > 0) {
                                result2 = respUci[0];
                            }
                            if (result2 != 0) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET: Get PDoA Offset failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            }
                            ByteBuffer buffer = ByteBuffer.wrap(respUci, 2, respUci.length - 2);
                            int i4 = buffer.get();
                            float[] pdoaOffsets = new float[i4];
                            int i5 = 0;
                            while (i5 < i4) {
                                String rxPair2 = rxPair;
                                int idx = buffer.get();
                                int result3 = result2;
                                int value = buffer.order(ByteOrder.LITTLE_ENDIAN).getShort() & UShort.MAX_VALUE;
                                byte[] uci2 = uci;
                                ByteBuffer buffer2 = buffer;
                                pdoaOffsets[i5] = UwbUtil.convertQFormatToFloat(UwbUtil.twos_compliment(value, 16), 9, 7);
                                if (idx == rxAntPairs3) {
                                    pdoaOffsets[i5] = pdoaOffsets[i5] + phaseOffset;
                                    phaseOffset = pdoaOffsets[i5];
                                }
                                i5++;
                                result2 = result3;
                                rxPair = rxPair2;
                                uci = uci2;
                                buffer = buffer2;
                            }
                            int result4 = 2;
                            int payloadLen = respUci.length;
                            ByteBuffer buffer3 = ByteBuffer.allocate(payloadLen).order(ByteOrder.LITTLE_ENDIAN);
                            buffer3.put(channel2);
                            buffer3.put(NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF);
                            buffer3.put((byte) i4);
                            int i6 = 0;
                            while (i6 < i4) {
                                byte idx2 = (byte) (i6 + 1);
                                buffer3.put(idx2);
                                buffer3.putShort((short) UwbUtil.twos_compliment(UwbUtil.convertFloatToQFormat(pdoaOffsets[i6], 9, 7), 16));
                                i6++;
                                result4 = result4;
                                channel2 = channel2;
                                rxAntPairs3 = rxAntPairs3;
                            }
                            int result5 = result4;
                            byte[] respUci2 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 17, buffer3.array());
                            if (respUci2 != null && respUci2.length > 0) {
                                result5 = respUci2[0];
                            }
                            if (result5 != 0) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET: Set PDoA Offset failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            } else if (UwbFactoryConstant.writeString(path2, Float.valueOf(phaseOffset))) {
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                                return;
                            } else {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET: Write to efs failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            }
                        } catch (NumberFormatException e15) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (NumberFormatException e16) {
                    }
                    break;
                case 24:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_PHASE_OFFSET");
                    String[] phaseData2 = (String[]) msg.obj;
                    String rxPair3 = phaseData2[1];
                    try {
                        byte channel3 = Byte.parseByte(phaseData2[0]);
                        switch (rxPair3) {
                            case "AOA_PORTRAIT":
                                rxAntPairs4 = 1;
                                break;
                            case "AOA_LANDSCAPE":
                                rxAntPairs4 = 2;
                                break;
                            case "P1:P2":
                                rxAntPairs4 = 1;
                                break;
                            case "P1:P3":
                                rxAntPairs4 = 2;
                                break;
                            default:
                                Log.w(UwbFactoryManager.TAG, "MSG_TEST_READ_PHASE_OFFSET: invalid Rx Antenna Pair");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                        }
                        int result6 = 2;
                        byte[] respUci3 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 18, UciBuilder.buildGetPdoaOffset(channel3, NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF));
                        if (respUci3 != null && respUci3.length > 0) {
                            result6 = respUci3[0];
                        }
                        if (result6 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_PHASE_OFFSET: Get PDoA Offset failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        float pdoaOffset = Float.MAX_VALUE;
                        ByteBuffer buffer4 = ByteBuffer.wrap(respUci3, 2, respUci3.length - 2);
                        byte noOfEntries = buffer4.get();
                        int i7 = 0;
                        while (i7 < noOfEntries) {
                            int idx3 = buffer4.get();
                            int value2 = buffer4.order(ByteOrder.LITTLE_ENDIAN).getShort() & UShort.MAX_VALUE;
                            if (idx3 == rxAntPairs4) {
                                pdoaOffset = UwbUtil.convertQFormatToFloat(UwbUtil.twos_compliment(value2, 16), 9, 7);
                            }
                            i7++;
                            rxAntPairs4 = rxAntPairs4;
                            channel3 = channel3;
                            phaseData2 = phaseData2;
                        }
                        if (pdoaOffset != Float.MAX_VALUE) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(Float.toString(pdoaOffset));
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (NumberFormatException e17) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 25:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_ESE_DO_BIND");
                    UwbFactoryManager.this.mEseDoBindObject = new Object();
                    ExecutorService executor3 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> eseDoBindTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda2
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m181xa39fa3be();
                        }
                    });
                    executor3.submit(eseDoBindTask);
                    int status3 = 2;
                    try {
                        status3 = eseDoBindTask.get(4000L, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e18) {
                        e18.printStackTrace();
                    } catch (ExecutionException e19) {
                        e19.printStackTrace();
                    } catch (TimeoutException e20) {
                        executor3.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_DO_BIND: Timeout occurred");
                    }
                    UwbFactoryManager.this.mEseDoBindObject = null;
                    if (status3 == 0) {
                        if (UwbFactoryManager.this.mSeBindingResult.getBindingState() == 1) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + UwbFactoryManager.this.mSeBindingResult.getRemainedBindingCount() + "," + UwbFactoryIntentManager.BOUND_UNLOCKED);
                            return;
                        } else if (UwbFactoryManager.this.mSeBindingResult.getBindingState() == 2) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + UwbFactoryManager.this.mSeBindingResult.getRemainedBindingCount() + "," + UwbFactoryIntentManager.BOUND_LOCKED);
                            return;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_DO_BIND: Undefined binding state");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    }
                    if (UwbFactoryManager.this.mSeBindingResult != null && UwbFactoryManager.this.mSeBindingResult.getBindingState() == 0) {
                        if (UwbFactoryManager.this.mSeBindingResult.getRemainedBindingCount() == 0) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG_COUNT," + UwbFactoryManager.this.mSeBindingResult.getRemainedBindingCount() + "," + UwbFactoryIntentManager.NOT_BOUND + UwbFactoryManager.this.mSeBindingResult.getBindingState());
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG_BIND," + UwbFactoryManager.this.mSeBindingResult.getRemainedBindingCount() + "," + UwbFactoryIntentManager.NOT_BOUND + UwbFactoryManager.this.mSeBindingResult.getBindingState());
                            return;
                        }
                    }
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 26:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_STATUS");
                    UwbFactoryManager.this.mEseGetBindingStatusObject = new Object();
                    ExecutorService executor4 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> eseGetBindingStatusTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda3
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m182xaac885ff();
                        }
                    });
                    executor4.submit(eseGetBindingStatusTask);
                    int status4 = 2;
                    try {
                        status4 = eseGetBindingStatusTask.get(4000L, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e21) {
                        e21.printStackTrace();
                    } catch (ExecutionException e22) {
                        e22.printStackTrace();
                    } catch (TimeoutException e23) {
                        executor4.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_STATUS: Timeout occurred");
                    }
                    UwbFactoryManager.this.mEseGetBindingStatusObject = null;
                    if (status4 == 0) {
                        if (UwbFactoryManager.this.mSeBindingStatus.getBindingStatus() == 0) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG_BIND," + UwbFactoryManager.this.mSeBindingStatus.getRemainedBindingCount() + "," + UwbFactoryManager.this.mSeBindingStatus.getRemainedSeBindingCount() + "," + UwbFactoryIntentManager.NOT_BOUND);
                            return;
                        }
                        if (UwbFactoryManager.this.mSeBindingStatus.getBindingStatus() == 1) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("NG_BIND," + UwbFactoryManager.this.mSeBindingStatus.getRemainedBindingCount() + "," + UwbFactoryManager.this.mSeBindingStatus.getRemainedSeBindingCount() + "," + UwbFactoryIntentManager.BOUND_UNLOCKED);
                            return;
                        } else if (UwbFactoryManager.this.mSeBindingStatus.getBindingStatus() == 2) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + UwbFactoryManager.this.mSeBindingStatus.getRemainedBindingCount() + "," + UwbFactoryManager.this.mSeBindingStatus.getRemainedSeBindingCount() + "," + UwbFactoryIntentManager.BOUND_LOCKED);
                            return;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_STATUS: Undefined binding state");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    }
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case 27:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_COUNT");
                    int result7 = 2;
                    byte[] respUci4 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 10, UciBuilder.buildSeGetBindingCount());
                    if (respUci4 != null && respUci4.length > 0) {
                        result7 = respUci4[0];
                    }
                    if (result7 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_COUNT: eSE Get Binding Count Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    }
                    SeBindingCount seBindingCount = UciParser.parseSeGetBindingCount(respUci4);
                    if (seBindingCount == null) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + seBindingCount.getRemainedSeBindingCount());
                        return;
                    }
                case 28:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_ESE_CONNECTIVITY");
                    UwbFactoryManager.this.mEseConnectivityTestObject = new Object();
                    ExecutorService executor5 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> eseConnectivityTestTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda4
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m183xb1f16840();
                        }
                    });
                    executor5.submit(eseConnectivityTestTask);
                    int status5 = 2;
                    try {
                        status5 = eseConnectivityTestTask.get(4000L, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e24) {
                        e24.printStackTrace();
                    } catch (ExecutionException e25) {
                        e25.printStackTrace();
                    } catch (TimeoutException e26) {
                        executor5.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_CONNECTIVITY: Timeout occurred");
                    }
                    UwbFactoryManager.this.mEseConnectivityTestObject = null;
                    if (status5 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 29:
                    final short count = (short) msg.arg1;
                    final short interval = (short) msg.arg2;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_ESE_LOOPBACK: count=" + ((int) count) + ", interval=" + ((int) interval));
                    UwbFactoryManager.this.mEseLoopbackTestObject = new Object();
                    ExecutorService executor6 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> eseLoopbackTestTask = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda5
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m184xb91a4a81(count, interval);
                        }
                    });
                    executor6.submit(eseLoopbackTestTask);
                    int timeout2 = count * (interval + 40);
                    int status6 = 2;
                    try {
                        status6 = eseLoopbackTestTask.get(timeout2, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e27) {
                        e27.printStackTrace();
                    } catch (ExecutionException e28) {
                        e28.printStackTrace();
                    } catch (TimeoutException e29) {
                        executor6.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_LOOPBACK: Timeout occurred");
                    }
                    UwbFactoryManager.this.mEseLoopbackTestObject = null;
                    if (status6 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK, " + UwbFactoryManager.this.mSeLoopbackTestResult);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 30:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_GET_CHIP_INFO");
                    String res34 = SamsungCalibrationData.getUwbChipInfo();
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(1, res34);
                    return;
                case 31:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SKIP_REGULATION");
                    UwbFactoryManager.this.mUwbExtrasAdapter.skipRegulation(true);
                    return;
                case 32:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_CHECK_ANTENNA_CONNECTION_STATUS");
                    int result8 = 2;
                    byte[] respUci5 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 255, UciBuilder.buildGetAntennaConnectionStatus());
                    if (respUci5 != null && respUci5.length > 0) {
                        result8 = respUci5[0];
                    }
                    if (result8 != 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    byte isConnected = respUci5[1];
                    if (isConnected != 1) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                case 33:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_OVERWRITE_PHASE_OFFSET");
                    String[] phaseData3 = (String[]) msg.obj;
                    String rxPair4 = phaseData3[1];
                    try {
                        byte channel4 = Byte.parseByte(phaseData3[0]);
                        try {
                            float phaseOffset2 = Float.parseFloat(phaseData3[2]);
                            switch (rxPair4) {
                                case "AOA_PORTRAIT":
                                    path3 = UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET;
                                    rxAntPairs5 = 1;
                                    break;
                                case "AOA_LANDSCAPE":
                                    path3 = UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET;
                                    rxAntPairs5 = 2;
                                    break;
                                case "P1:P2":
                                    path3 = UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET;
                                    rxAntPairs5 = 1;
                                    break;
                                case "P1:P3":
                                    path3 = UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET;
                                    rxAntPairs5 = 2;
                                    break;
                                default:
                                    Log.w(UwbFactoryManager.TAG, "MSG_TEST_OVERWRITE_PHASE_OFFSET: invalid Rx Antenna Pair");
                                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                    return;
                            }
                            int result9 = 2;
                            byte[] uci3 = UciBuilder.buildGetPdoaOffset(channel4, NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF);
                            byte[] respUci6 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 18, uci3);
                            if (respUci6 != null && respUci6.length > 0) {
                                result9 = respUci6[0];
                            }
                            if (result9 != 0) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_OVERWRITE_PHASE_OFFSET: Get PDoA Offset failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            }
                            ByteBuffer buffer5 = ByteBuffer.wrap(respUci6, 2, respUci6.length - 2);
                            int i8 = buffer5.get();
                            float[] pdoaOffsets2 = new float[i8];
                            int i9 = 0;
                            while (i9 < i8) {
                                String rxPair5 = rxPair4;
                                int idx4 = buffer5.get();
                                int result10 = result9;
                                int value3 = buffer5.order(ByteOrder.LITTLE_ENDIAN).getShort() & UShort.MAX_VALUE;
                                byte[] uci4 = uci3;
                                ByteBuffer buffer6 = buffer5;
                                pdoaOffsets2[i9] = UwbUtil.convertQFormatToFloat(UwbUtil.twos_compliment(value3, 16), 9, 7);
                                if (idx4 == rxAntPairs5) {
                                    pdoaOffsets2[i9] = phaseOffset2;
                                }
                                i9++;
                                result9 = result10;
                                rxPair4 = rxPair5;
                                uci3 = uci4;
                                buffer5 = buffer6;
                            }
                            int result11 = 2;
                            int payloadLen2 = respUci6.length;
                            ByteBuffer buffer7 = ByteBuffer.allocate(payloadLen2).order(ByteOrder.LITTLE_ENDIAN);
                            buffer7.put(channel4);
                            buffer7.put(NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF);
                            buffer7.put((byte) i8);
                            int i10 = 0;
                            while (i10 < i8) {
                                byte idx5 = (byte) (i10 + 1);
                                buffer7.put(idx5);
                                buffer7.putShort((short) UwbUtil.twos_compliment(UwbUtil.convertFloatToQFormat(pdoaOffsets2[i10], 9, 7), 16));
                                i10++;
                                result11 = result11;
                                channel4 = channel4;
                                rxAntPairs5 = rxAntPairs5;
                            }
                            int result12 = result11;
                            byte[] respUci7 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 17, buffer7.array());
                            if (respUci7 != null && respUci7.length > 0) {
                                result12 = respUci7[0];
                            }
                            if (result12 != 0) {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_OVERWRITE_PHASE_OFFSET: Set PDoA Offset failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            } else if (UwbFactoryConstant.writeString(path3, Float.valueOf(phaseOffset2))) {
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                                return;
                            } else {
                                Log.e(UwbFactoryManager.TAG, "MSG_TEST_WRITE_PHASE_OFFSET: Write to efs failed");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            }
                        } catch (NumberFormatException e30) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (NumberFormatException e31) {
                    }
                    break;
                case 34:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_WRITE_ALL_TX_POWER");
                    String[] sDataArray4 = (String[]) msg.obj;
                    try {
                        int rangingTxPowerCh5 = Integer.parseInt(sDataArray4[0]);
                        int aoaTxPowerCh5 = Integer.parseInt(sDataArray4[1]);
                        int rangingTxPowerCh9 = Integer.parseInt(sDataArray4[2]);
                        int aoaTxPowerCh9 = Integer.parseInt(sDataArray4[3]);
                        boolean result13 = UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH5_RANGING_TX_POWER_CAL, Integer.valueOf(rangingTxPowerCh5));
                        if (!result13) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        boolean result14 = UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH5_AOA_TX_POWER_CAL, Integer.valueOf(aoaTxPowerCh5));
                        if (!result14) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        boolean result15 = UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH9_RANGING_TX_POWER_CAL, Integer.valueOf(rangingTxPowerCh9));
                        if (!result15) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        boolean result16 = UwbFactoryConstant.writeString(UwbFactoryConstant.PATH_CH9_AOA_TX_POWER_CAL, Integer.valueOf(aoaTxPowerCh9));
                        if (result16) {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } catch (Exception e32) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_WRITE_ALL_TX_POWER: Exception occurred");
                        e32.printStackTrace();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case 35:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_ALL_PHASE_OFFSET_FROM_EFS");
                    String azimuthPdoaOffsetCh9 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET);
                    String elevationPdoaOffsetCh9 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET);
                    if (azimuthPdoaOffsetCh9 == null || elevationPdoaOffsetCh9 == null) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    }
                    String res35 = azimuthPdoaOffsetCh9 + "," + elevationPdoaOffsetCh9;
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + res35);
                    return;
                case 36:
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_ALL_TX_POWER_FROM_EFS");
                    String rangingTxPowerCh6 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH5_RANGING_TX_POWER_CAL);
                    String aoaTxPowerCh6 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH5_AOA_TX_POWER_CAL);
                    String rangingTxPowerCh10 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH9_RANGING_TX_POWER_CAL);
                    String aoaTxPowerCh10 = UwbFactoryConstant.readString(UwbFactoryConstant.PATH_CH9_AOA_TX_POWER_CAL);
                    if (rangingTxPowerCh6 == null || aoaTxPowerCh6 == null || rangingTxPowerCh10 == null || aoaTxPowerCh10 == null) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    }
                    String res36 = rangingTxPowerCh6 + "," + aoaTxPowerCh6 + "," + rangingTxPowerCh10 + "," + aoaTxPowerCh10;
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + res36);
                    return;
                case 37:
                    String ant = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_RX_ANTENNA: ant=" + ant);
                    if (ant.equals(UwbFactoryConstant.ANT_AOA_PORTRAIT)) {
                        tx3 = 2;
                        rxAntConfig = SamsungCalibrationData.getRxAntennaConfiguration(1, 9);
                    } else if (ant.equals(UwbFactoryConstant.ANT_AOA_LANDSCAPE)) {
                        tx3 = 2;
                        rxAntConfig = SamsungCalibrationData.getRxAntennaConfiguration(2, 9);
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_RX_ANTENNA: Undefined ANT");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res37 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx(rxAntConfig.getRxAntMode(), rxAntConfig.getRxAntPairs()).setAntennasConfigTx(tx3, (byte) 0).build());
                    if (res37 == 0) {
                        this.mCurrentTxAntenna = tx3;
                        this.mCurrentRxAntenna = rxAntConfig.getRxAntPairs()[0];
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_RX_ANTENNA: setExtAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case UwbFactoryConstant.MSG_CUSTOM_RANGING_ON_WITH_INITIATOR /* 200 */:
                    Log.i(UwbFactoryManager.TAG, "MSG_CUSTOM_RANGING_ON_WITH_INITIATOR");
                    int res38 = UwbFactoryManager.this.mUwbExtrasAdapter.setAppConfigurations(this.mCurrentSessionId, new AppConfigParameters.Builder().setDeviceRole((byte) 1).setDeviceType((byte) 1).setDstMacAddress(UwbUtil.getByteArray(this.mDeviceMacAddress)).setDeviceMacAddress(UwbUtil.getByteArray(this.mDstMacAddress)).build());
                    if (res38 == 0) {
                        this.mCurrentRangingCount = 0;
                        this.mMaxRangingCount = Integer.MAX_VALUE;
                        int res39 = UwbFactoryManager.this.mUwbAdapter.rangingStart(this.mCurrentSessionId);
                        if (res39 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_RANGING_ON_WITH_INITIATOR: rangingStart Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        }
                    }
                    Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_RANGING_ON_WITH_INITIATOR: setAppConfigurations Failed");
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                    return;
                case UwbFactoryConstant.MSG_CUSTOM_RANGING_STOP /* 201 */:
                    Log.i(UwbFactoryManager.TAG, "MSG_CUSTOM_RANGING_STOP");
                    int result17 = UwbFactoryManager.this.mUwbAdapter.rangingStop(this.mCurrentSessionId);
                    if (result17 != 0) {
                        Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_RANGING_STOP: Ranging Stop Failed, result=" + result17);
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    } else {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    }
                case UwbFactoryConstant.MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP /* 202 */:
                    String[] phaseData4 = (String[]) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP: channel=" + phaseData4[0] + ", rxPair=" + phaseData4[1] + ", phaseFlip=" + phaseData4[2]);
                    String rxPair6 = phaseData4[1];
                    try {
                        byte channel5 = Byte.parseByte(phaseData4[0]);
                        byte phaseFlip = Byte.parseByte(phaseData4[2]);
                        if (phaseFlip != 0 && phaseFlip != 1) {
                            try {
                                Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP: invalid Phase Flip value");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            } catch (NumberFormatException e33) {
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                            }
                        }
                        switch (rxPair6) {
                            case "P1:P2":
                                rxAntPairs6 = 1;
                                break;
                            case "P1:P3":
                                rxAntPairs6 = 2;
                                break;
                            default:
                                Log.w(UwbFactoryManager.TAG, "MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP: invalid Rx Antenna Pair");
                                UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                                return;
                        }
                        int result18 = 2;
                        byte[] respUci8 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 18, UciBuilder.buildGetAntennaSpacing(channel5, UwbFactoryConstant.PREAMBLE_CODE_INDEX_25));
                        if (respUci8 != null && respUci8.length > 0) {
                            result18 = respUci8[0];
                        }
                        if (result18 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP: Get Antenna Spacing failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        ByteBuffer buffer8 = ByteBuffer.wrap(respUci8, 2, respUci8.length - 2);
                        int i11 = buffer8.get();
                        int[] antennaSpacing = new int[i11];
                        int msgType2 = 0;
                        while (msgType2 < i11) {
                            String[] phaseData5 = phaseData4;
                            int idx6 = buffer8.get();
                            int result19 = result18;
                            int value4 = buffer8.order(ByteOrder.LITTLE_ENDIAN).getShort() & UShort.MAX_VALUE;
                            antennaSpacing[msgType2] = value4;
                            if (idx6 == rxAntPairs6) {
                                int rxAntPairs14 = value4 & 32767;
                                antennaSpacing[msgType2] = rxAntPairs14 | (phaseFlip << UwbFactoryConstant.KEY_ROTATION_RATE_15);
                            }
                            msgType2++;
                            result18 = result19;
                            phaseData4 = phaseData5;
                            rxAntPairs6 = rxAntPairs6;
                        }
                        int result20 = 2;
                        int payloadLen3 = respUci8.length;
                        ByteBuffer buffer9 = ByteBuffer.allocate(payloadLen3).order(ByteOrder.LITTLE_ENDIAN);
                        buffer9.put(channel5);
                        buffer9.put(UwbFactoryConstant.PREAMBLE_CODE_INDEX_25);
                        buffer9.put((byte) i11);
                        int i12 = 0;
                        while (i12 < i11) {
                            byte idx7 = (byte) (i12 + 1);
                            buffer9.put(idx7);
                            int result21 = result20;
                            int result22 = antennaSpacing[i12];
                            buffer9.putShort((short) result22);
                            i12++;
                            result20 = result21;
                        }
                        int result23 = result20;
                        byte[] respUci9 = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 17, buffer9.array());
                        if (respUci9 != null && respUci9.length > 0) {
                            result23 = respUci9[0];
                        }
                        if (result23 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP: Set Antenna Spacing failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        } else {
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                            return;
                        }
                    } catch (NumberFormatException e34) {
                    }
                    break;
                case UwbFactoryConstant.MSG_TEST_SET_TX_ANTENNA_DEPRECATED /* 500 */:
                    String txAnt2 = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA_DEPRECATED: txAnt=" + txAnt2);
                    if (txAnt2.equals(UwbFactoryConstant.METAL_1)) {
                        tx4 = 1;
                    } else if (txAnt2.equals(UwbFactoryConstant.PATCH_1)) {
                        tx4 = 2;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA_DEPRECATED: Undefined Tx ANT");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    SamsungCalibrationData.RxAntennaConfiguration rxAntConfig2 = SamsungCalibrationData.getRxAntennaConfiguration(1, 9);
                    int res40 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx(rxAntConfig2.getRxAntMode(), rxAntConfig2.getRxAntPairs()).setAntennasConfigTx(tx4, (byte) 0).build());
                    if (res40 == 0) {
                        this.mCurrentTxAntenna = tx4;
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_TX_ANTENNA_DEPRECATED: setExtAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case UwbFactoryConstant.MSG_TEST_SET_RX_ANTENNA_DEPRECATED /* 501 */:
                    String rxAnt2 = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA_DEPRECATED: rxAnt=" + rxAnt2);
                    byte[] bArr3 = new byte[2];
                    if (rxAnt2.equals(UwbFactoryConstant.METAL_1_PATCH_2)) {
                        tx5 = 1;
                        SamsungCalibrationData.RxAntennaConfiguration rxAntConfig3 = SamsungCalibrationData.getRxAntennaConfiguration(1, 9);
                        rxAntMode = rxAntConfig3.getRxAntMode();
                        rxAntPairs7 = rxAntConfig3.getRxAntPairs();
                        this.mCurrentTxAntenna = (byte) 1;
                        this.mCurrentRxAntenna = (byte) 1;
                    } else if (rxAnt2.equals(UwbFactoryConstant.METAL_1_PATCH_3)) {
                        tx5 = 1;
                        SamsungCalibrationData.RxAntennaConfiguration rxAntConfig4 = SamsungCalibrationData.getRxAntennaConfiguration(2, 9);
                        rxAntMode = rxAntConfig4.getRxAntMode();
                        rxAntPairs7 = rxAntConfig4.getRxAntPairs();
                        this.mCurrentTxAntenna = (byte) 1;
                        this.mCurrentRxAntenna = (byte) 2;
                    } else if (rxAnt2.equals(UwbFactoryConstant.PATCH_1_PATCH_2)) {
                        tx5 = 2;
                        SamsungCalibrationData.RxAntennaConfiguration rxAntConfig5 = SamsungCalibrationData.getRxAntennaConfiguration(1, 9);
                        rxAntMode = rxAntConfig5.getRxAntMode();
                        rxAntPairs7 = rxAntConfig5.getRxAntPairs();
                        this.mCurrentTxAntenna = (byte) 2;
                        this.mCurrentRxAntenna = (byte) 1;
                    } else if (rxAnt2.equals(UwbFactoryConstant.PATCH_1_PATCH_3)) {
                        tx5 = 2;
                        SamsungCalibrationData.RxAntennaConfiguration rxAntConfig6 = SamsungCalibrationData.getRxAntennaConfiguration(2, 9);
                        rxAntMode = rxAntConfig6.getRxAntMode();
                        rxAntPairs7 = rxAntConfig6.getRxAntPairs();
                        this.mCurrentTxAntenna = (byte) 2;
                        this.mCurrentRxAntenna = (byte) 2;
                    } else if (rxAnt2.equals(UwbFactoryConstant.METAL_2)) {
                        tx5 = 1;
                        rxAntMode = 1;
                        rxAntPairs7 = new byte[]{5};
                        this.mCurrentTxAntenna = (byte) 1;
                        this.mCurrentRxAntenna = (byte) 3;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA_DEPRECATED: Undefined Rx ANT");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    int res41 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx(rxAntMode, rxAntPairs7).setAntennasConfigTx(tx5, (byte) 0).build());
                    if (res41 == 0) {
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_OK);
                        return;
                    } else {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_SET_RX_ANTENNA_DEPRECATED: setExtAppConfiguration Failed");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                case UwbFactoryConstant.MSG_TEST_READ_RSSI_DEPRECATED /* 502 */:
                    String rxAntennaToRead3 = (String) msg.obj;
                    Log.i(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: rxAnt=" + rxAntennaToRead3);
                    if (rxAntennaToRead3.equals(UwbFactoryConstant.RX1)) {
                        byte rxAntId3 = this.mCurrentRxAntenna;
                        if (rxAntId3 == 1) {
                            rxAntId2 = 3;
                        } else if (rxAntId3 == 2) {
                            rxAntId2 = 4;
                        } else if (rxAntId3 == 3) {
                            rxAntId2 = 5;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: Undefined Rx Antenna Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res42 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx((byte) 1, new byte[]{rxAntId2}).build());
                        if (res42 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: setExtAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } else if (rxAntennaToRead3.equals(UwbFactoryConstant.RX2)) {
                        byte b4 = this.mCurrentTxAntenna;
                        if (b4 == 1) {
                            if (this.mCurrentRxAntenna == 3) {
                                rxAntId = 5;
                            } else {
                                rxAntId = 1;
                            }
                        } else if (b4 == 2) {
                            rxAntId = 2;
                        } else {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: Undefined Rx Antenna Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                        int res43 = UwbFactoryManager.this.mUwbExtrasAdapter.setExtAppConfigurations(this.mCurrentSessionId, new AppConfigExtParameters.Builder().setAntennasConfigRx((byte) 1, new byte[]{rxAntId}).build());
                        if (res43 != 0) {
                            Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: setExtAppConfigurations Failed");
                            UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                            return;
                        }
                    } else if (!rxAntennaToRead3.equals(UwbFactoryConstant.RX1_RX2) && !rxAntennaToRead3.equals(UwbFactoryConstant.RX2_RX1)) {
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: Undefined Rx Ant to Read");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    UwbFactoryManager.this.mTestPerRxObject = new Object();
                    ExecutorService executor7 = Executors.newSingleThreadExecutor();
                    FutureTask<Integer> TestPerRxTask2 = new FutureTask<>(new Callable() { // from class: com.samsung.android.uwb_extension.factory.UwbFactoryManager$UwbFactoryHandler$$ExternalSyntheticLambda6
                        @Override // java.util.concurrent.Callable
                        public final Object call() {
                            return this.f$0.m185xc0432cc2();
                        }
                    });
                    executor7.submit(TestPerRxTask2);
                    int timeout3 = this.mPerRxTimeout;
                    int status7 = 2;
                    try {
                        status7 = TestPerRxTask2.get(timeout3, TimeUnit.MILLISECONDS).intValue();
                    } catch (InterruptedException e35) {
                        e35.printStackTrace();
                    } catch (ExecutionException e36) {
                        e36.printStackTrace();
                    } catch (TimeoutException e37) {
                        executor7.shutdownNow();
                        Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: Timeout occurred");
                    }
                    UwbFactoryManager.this.mTestPerRxObject = null;
                    String str4 = BuildConfig.FLAVOR;
                    if (status7 != 0) {
                        UwbFactoryManager.this.mSamsungUwbTestManager.stopTestModeSession();
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    if (rxAntennaToRead3.equals(UwbFactoryConstant.RX1)) {
                        float rssi3 = 0.0f;
                        float snr2 = 0.0f;
                        byte b5 = this.mCurrentRxAntenna;
                        if (b5 == 1) {
                            rssi3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[1];
                            snr2 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[1];
                        } else if (b5 == 2) {
                            rssi3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[0];
                            snr2 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[0];
                        } else if (b5 == 3) {
                            int len2 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi().length;
                            int i13 = 0;
                            while (i13 < len2) {
                                String str5 = str4;
                                if (UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i13] < 0.0f && UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i13] > -90.0f) {
                                    rssi3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i13];
                                    snr2 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[i13];
                                }
                                i13++;
                                str4 = str5;
                            }
                        }
                        str = String.format(Locale.US, "%.2f,%.2f", Float.valueOf(rssi3), Float.valueOf(snr2));
                    } else if (rxAntennaToRead3.equals(UwbFactoryConstant.RX2)) {
                        float rssi4 = 0.0f;
                        float snr3 = 0.0f;
                        if (this.mCurrentRxAntenna == 3) {
                            int len3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi().length;
                            for (int i14 = 0; i14 < len3; i14++) {
                                if (UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i14] < 0.0f && UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i14] > -90.0f) {
                                    rssi4 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[i14];
                                    snr3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[i14];
                                }
                            }
                            i = 2;
                        } else {
                            i = 2;
                            rssi4 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[2];
                            snr3 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[2];
                        }
                        Locale locale = Locale.US;
                        Object[] objArr = new Object[i];
                        objArr[0] = Float.valueOf(rssi4);
                        objArr[1] = Float.valueOf(snr3);
                        str = String.format(locale, "%.2f,%.2f", objArr);
                    } else if (rxAntennaToRead3.equals(UwbFactoryConstant.RX1_RX2)) {
                        float rssi5 = 0.0f;
                        float snr4 = 0.0f;
                        byte b6 = this.mCurrentRxAntenna;
                        if (b6 == 1) {
                            rssi5 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[1];
                            snr4 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[1];
                            c = 0;
                        } else if (b6 != 2) {
                            c = 0;
                        } else {
                            c = 0;
                            rssi5 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[0];
                            snr4 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[0];
                        }
                        Locale locale2 = Locale.US;
                        Object[] objArr2 = new Object[4];
                        objArr2[c] = Float.valueOf(rssi5);
                        objArr2[1] = Float.valueOf(snr4);
                        objArr2[2] = Float.valueOf(UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[2]);
                        objArr2[3] = Float.valueOf(UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[2]);
                        str = String.format(locale2, "%.2f,%.2f,%.2f,%.2f", objArr2);
                    } else if (rxAntennaToRead3.equals(UwbFactoryConstant.RX2_RX1)) {
                        float rssi6 = 0.0f;
                        float snr5 = 0.0f;
                        byte b7 = this.mCurrentRxAntenna;
                        if (b7 == 1) {
                            rssi6 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[1];
                            snr5 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[1];
                        } else if (b7 == 2) {
                            rssi6 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[0];
                            snr5 = UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[0];
                        }
                        str = String.format(Locale.US, "%.2f,%.2f,%.2f,%.2f", Float.valueOf(UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRssi()[2]), Float.valueOf(UwbFactoryManager.this.mTestRxPacketErrorRateResult.getSnr()[2]), Float.valueOf(rssi6), Float.valueOf(snr5));
                    } else {
                        String str6 = UwbFactoryManager.TAG;
                        Log.e(str6, "MSG_TEST_READ_RSSI_DEPRECATED: Undefined Rx Ant to Read");
                        UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse(UwbFactoryIntentManager.DATA_NG);
                        return;
                    }
                    UwbFactoryManager.this.mUwbFactoryIntentManager.sendResponse("OK," + (str + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAttempts() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAcqDetect() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getAcqReject() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getRxFail() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getPhrDecError() + "," + UwbFactoryManager.this.mTestRxPacketErrorRateResult.getPsduDecError()));
                    return;
                default:
                    return;
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$0$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m179x954ddf3c() throws Exception {
            synchronized (UwbFactoryManager.this.mTestLoopbackObject) {
                int result = UwbFactoryManager.this.mSamsungUwbTestManager.startTestModeSession(2, HexDump.hexStringToByteArray(UwbFactoryConstant.PSDU));
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_RF_LOOPBACK: startTestModeSession Failed");
                    return 2;
                }
                UwbFactoryManager.this.mTestRfLoopbackResult = null;
                UwbFactoryManager.this.mTestLoopbackObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mTestRfLoopbackResult != null && UwbFactoryManager.this.mTestRfLoopbackResult.getStatus() == 0) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$1$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m180x9c76c17d() throws Exception {
            synchronized (UwbFactoryManager.this.mTestPerRxObject) {
                int result = UwbFactoryManager.this.mSamsungUwbTestManager.startTestModeSession(1, HexDump.hexStringToByteArray(UwbFactoryConstant.PSDU));
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI: startTestModeSession Failed");
                    return 2;
                }
                UwbFactoryManager.this.mTestRxPacketErrorRateResult = null;
                UwbFactoryManager.this.mTestPerRxObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mTestRxPacketErrorRateResult != null && UwbFactoryManager.this.mTestRxPacketErrorRateResult.getStatus() == 0) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$2$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m181xa39fa3be() throws Exception {
            synchronized (UwbFactoryManager.this.mEseDoBindObject) {
                int result = 2;
                byte[] uci = UciBuilder.buildSeDoBind();
                byte[] respUci = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 1, uci);
                if (respUci != null && respUci.length > 0) {
                    result = respUci[0];
                }
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_DO_BIND: eSE Do Bind Failed");
                    return 2;
                }
                UwbFactoryManager.this.mSeBindingResult = null;
                UwbFactoryManager.this.mEseDoBindObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mSeBindingResult != null && UwbFactoryManager.this.mSeBindingResult.getStatus() == 80) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$3$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m182xaac885ff() throws Exception {
            synchronized (UwbFactoryManager.this.mEseGetBindingStatusObject) {
                int result = 2;
                byte[] uci = UciBuilder.buildSeGetBindingStatus();
                byte[] respUci = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 12, uci);
                if (respUci != null && respUci.length > 0) {
                    result = respUci[0];
                }
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_GET_ESE_BINDING_STATUS: eSE Get Binding Status Failed");
                    return 2;
                }
                UwbFactoryManager.this.mSeBindingStatus = null;
                UwbFactoryManager.this.mEseGetBindingStatusObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mSeBindingStatus != null) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$4$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m183xb1f16840() throws Exception {
            synchronized (UwbFactoryManager.this.mEseConnectivityTestObject) {
                int result = 2;
                byte[] uci = UciBuilder.buildTestSeConnectivity();
                byte[] respUci = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 14, uci);
                if (respUci != null && respUci.length > 0) {
                    result = respUci[0];
                }
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_CONNECTIVITY: eSE Connectivity Test Failed");
                    return 2;
                }
                UwbFactoryManager.this.mSeConnectivityTestResult = null;
                UwbFactoryManager.this.mEseConnectivityTestObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mSeConnectivityTestResult != null && UwbFactoryManager.this.mSeConnectivityTestResult.getStatus() == 0) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$5$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m184xb91a4a81(short count, short interval) throws Exception {
            synchronized (UwbFactoryManager.this.mEseLoopbackTestObject) {
                int result = 2;
                byte[] uci = UciBuilder.buildTestSeLoop(count, interval);
                byte[] respUci = UwbFactoryManager.this.mIVendorExtension.sendVendorUciMessage(14, 13, uci);
                if (respUci != null && respUci.length > 0) {
                    result = respUci[0];
                }
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_ESE_LOOPBACK: eSE Loopback Test Failed");
                    return 2;
                }
                UwbFactoryManager.this.mSeLoopbackTestResult = null;
                UwbFactoryManager.this.mEseLoopbackTestObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mSeLoopbackTestResult != null && UwbFactoryManager.this.mSeLoopbackTestResult.getStatus() == 0) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }

        /* JADX INFO: renamed from: lambda$handleMessage$6$com-samsung-android-uwb_extension-factory-UwbFactoryManager$UwbFactoryHandler, reason: not valid java name */
        /* synthetic */ Integer m185xc0432cc2() throws Exception {
            synchronized (UwbFactoryManager.this.mTestPerRxObject) {
                int result = UwbFactoryManager.this.mSamsungUwbTestManager.startTestModeSession(1, HexDump.hexStringToByteArray(UwbFactoryConstant.PSDU));
                if (result != 0) {
                    Log.e(UwbFactoryManager.TAG, "MSG_TEST_READ_RSSI_DEPRECATED: startTestModeSession Failed");
                    return 2;
                }
                UwbFactoryManager.this.mTestRxPacketErrorRateResult = null;
                UwbFactoryManager.this.mTestPerRxObject.wait();
                int status = 2;
                if (UwbFactoryManager.this.mTestRxPacketErrorRateResult != null && UwbFactoryManager.this.mTestRxPacketErrorRateResult.getStatus() == 0) {
                    status = 0;
                }
                return Integer.valueOf(status);
            }
        }
    }

    public void applyCalibration() {
        String str = TAG;
        Log.d(str, "applyCalibration: Enter");
        if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH5_VCO_PLL_CAL)) {
            short vcoPll = UwbFactoryConstant.readStringAsShort(UwbFactoryConstant.PATH_CH5_VCO_PLL_CAL);
            byte[] vcoPllValue = ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(vcoPll).array();
            CalibrationResult res = this.mVendor.setCalibration((byte) 5, (byte) 0, vcoPllValue);
            Log.d(str, "CHANNEL_5, CAL_RF_PLL_VCO result: " + res.getStatus());
        } else {
            Log.e(str, "CHANNEL_5, CAL_RF_PLL_VCO is NULL");
        }
        if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH9_VCO_PLL_CAL)) {
            short vcoPll2 = UwbFactoryConstant.readStringAsShort(UwbFactoryConstant.PATH_CH9_VCO_PLL_CAL);
            byte[] vcoPllValue2 = ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(vcoPll2).array();
            CalibrationResult res2 = this.mVendor.setCalibration((byte) 9, (byte) 0, vcoPllValue2);
            Log.d(str, "CHANNEL_9, CAL_RF_PLL_VCO result: " + res2.getStatus());
        } else {
            Log.e(str, "CHANNEL_9, CAL_RF_PLL_VCO is NULL");
        }
        if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH5_RANGING_TX_POWER_CAL)) {
            byte[] txPower = {2, 1, UwbFactoryConstant.readStringAsByte(UwbFactoryConstant.PATH_CH5_RANGING_TX_POWER_CAL), (byte) SamsungCalibrationData.getTxPowerDeltaPeakRangingAntenna(5), 2, UwbFactoryConstant.readStringAsByte(UwbFactoryConstant.PATH_CH5_AOA_TX_POWER_CAL), (byte) SamsungCalibrationData.getTxPowerDeltaPeakAoaAntenna(5)};
            CalibrationResult res3 = this.mVendor.setCalibration((byte) 5, UwbUciConstants.POWER_OFFSET_47_DBM, txPower);
            Log.d(str, "CHANNEL_5, CAL_PATCH_TX_POWER result: " + res3.getStatus());
        } else {
            Log.d(str, "CHANNEL_5, CAL_PATCH_TX_POWER is NULL");
        }
        if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH9_RANGING_TX_POWER_CAL)) {
            byte[] txPower2 = {2, 1, UwbFactoryConstant.readStringAsByte(UwbFactoryConstant.PATH_CH9_RANGING_TX_POWER_CAL), (byte) SamsungCalibrationData.getTxPowerDeltaPeakRangingAntenna(9), 2, UwbFactoryConstant.readStringAsByte(UwbFactoryConstant.PATH_CH9_AOA_TX_POWER_CAL), (byte) SamsungCalibrationData.getTxPowerDeltaPeakAoaAntenna(9)};
            CalibrationResult res4 = this.mVendor.setCalibration((byte) 9, UwbUciConstants.POWER_OFFSET_47_DBM, txPower2);
            Log.d(str, "CHANNEL_9, CAL_PATCH_TX_POWER result: " + res4.getStatus());
        } else {
            Log.d(str, "CHANNEL_9, CAL_PATCH_TX_POWER is NULL");
        }
        if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET)) {
            int result = 2;
            byte[] uci = UciBuilder.buildGetPdoaOffset((byte) 9, NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF);
            byte[] respUci = this.mIVendorExtension.sendVendorUciMessage(14, 18, uci);
            if (respUci != null && respUci.length > 0) {
                result = respUci[0];
            }
            if (result == 0 && respUci.length > 2) {
                float[] pdoaOffsets = {0.0f, 0.0f};
                ByteBuffer buffer = ByteBuffer.wrap(respUci, 2, respUci.length - 2);
                byte noOfEntries = buffer.get();
                for (int i = 0; i < noOfEntries; i++) {
                    buffer.get();
                    int value = buffer.order(ByteOrder.LITTLE_ENDIAN).getShort() & UShort.MAX_VALUE;
                    pdoaOffsets[i] = UwbUtil.convertQFormatToFloat(UwbUtil.twos_compliment(value, 16), 9, 7);
                }
                if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET)) {
                    pdoaOffsets[0] = UwbFactoryConstant.readStringAsFloat(UwbFactoryConstant.PATH_CH9_PORTRAIT_PDOA_OFFSET);
                }
                if (UwbFactoryConstant.isFileExists(UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET)) {
                    pdoaOffsets[1] = UwbFactoryConstant.readStringAsFloat(UwbFactoryConstant.PATH_CH9_LANDSCAPE_PDOA_OFFSET);
                }
                ByteBuffer buffer2 = ByteBuffer.allocate(7).order(ByteOrder.LITTLE_ENDIAN);
                buffer2.put(noOfEntries);
                for (int i2 = 0; i2 < noOfEntries; i2++) {
                    byte idx = (byte) (i2 + 1);
                    buffer2.put(idx);
                    buffer2.putShort((short) UwbUtil.twos_compliment(UwbUtil.convertFloatToQFormat(pdoaOffsets[i2], 9, 7), 16));
                }
                buffer2.rewind();
                CalibrationResult res5 = this.mVendor.setCalibration((byte) 9, NxpUwbDebugConfigInfo.UCI_PARAM_ID_DATA_LOGGER_NTF, buffer2.array());
                Log.d(TAG, "CHANNEL_9, CAL_AOA_PHASE_OFFSET result: " + res5.getStatus());
                return;
            }
            Log.e(str, "applyCalibration: Get PDoA Offset failed");
            return;
        }
        Log.e(str, "CHANNEL_9, CAL_AOA_PHASE_OFFSET is NULL");
    }
}
