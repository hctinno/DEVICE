package egis.client.api;

import android.content.Context;
import android.graphics.Bitmap;
import android.os.Handler;
import android.os.Message;
import android.util.Log;
import android.util.SparseArray;
import egis.finger.ICS1Native;
import egis.finger.hidl.FPCS1HidlNative;
import egistec.csa.client.api.Fingerprint;
import egistec.csa.client.api.IFingerprint;
import java.io.UnsupportedEncodingException;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/* JADX INFO: loaded from: classes.dex */
public class EgisFingerprint implements IFingerprint {
    public static final int ACCURACY_HIGH = 2;
    public static final int ACCURACY_LOW = 0;
    public static final int ACCURACY_REGULAR = 1;
    public static final int ACCURACY_VERY_HIGH = 3;
    public static final int CAPTURE_COMPLETED = 1042;
    public static final int CAPTURE_FAILED = 1045;
    public static final int CAPTURE_FINISHED = 1043;
    public static final int CAPTURE_READY = 1040;
    public static final int CAPTURE_STARTED = 1041;
    public static final int CAPTURE_SUCCESS = 1044;
    public static final int ENROLL_BITMAP = 1005;
    public static final int ENROLL_FAILED = 1002;
    public static final int ENROLL_FAILURE_CANCELED = 1003;
    public static final int ENROLL_FAULURE_ENROLL_FAILURE_EXCEED_MAX_TRIAL = 1004;
    public static final int ENROLL_STATUS = 1000;
    public static final int ENROLL_SUCCESS = 1001;
    public static final int EVT_ERROR = 2020;
    public static final int FACTORY_TEST_EVT_SNSR_TEST_PUT = 285212677;
    public static final int FACTORY_TEST_EVT_SNSR_TEST_SCRIPT_END = 285212676;
    public static final int FACTORY_TEST_EVT_SNSR_TEST_SCRIPT_START = 285212675;
    public static final int FACTORY_WRITE_EEPROM_SCRIPT_END = 2032;
    public static final int FACTORY_WRITE_EEPROM_SCRIPT_START = 2031;
    private static final String FPID_PREFIX = "EGISFPID";
    public static final int IDENTIFY_FAILED = 1021;
    public static final int IDENTIFY_FAILURE_BAD_QUALITY = 1025;
    public static final int IDENTIFY_FAILURE_CANCELED = 1022;
    public static final int IDENTIFY_FAILURE_NOT_MATCH = 1024;
    public static final int IDENTIFY_FAILURE_TIMEOUT = 1023;
    public static final int IDENTIFY_SUCCESS = 1020;
    public static final String JAR_VERSION = "35";
    public static final String MAJOR_VERSION = "1";
    private static final int MAP_H = 256;
    private static final int MAP_W = 256;
    public static final int MAX_ENROLL_FINGERS = 5;
    public static final int OP_TYPE_ENROLL = 101;
    public static final int OP_TYPE_VERIFY = 102;
    private static final String PASSOWORD_PREFIX = "EGISPWD";
    private static final String PASSWORD = "egistec";
    public static final int PAUSE_ENROLL = 2010;
    public static final int QUALITY_DUPLICATED_SCANNED_IMAGE = 256;
    public static final int QUALITY_EMPTY_TOUCH = 536870912;
    public static final int QUALITY_FAILED = 268435456;
    public static final int QUALITY_FINGER_TOO_THIN = 128;
    public static final int QUALITY_GOOD = 0;
    public static final int QUALITY_NOT_A_FINGER_SWIPE = 16;
    public static final int QUALITY_OFFSET_TOO_FAR_LEFT = 1;
    public static final int QUALITY_OFFSET_TOO_FAR_RIGHT = 2;
    public static final int QUALITY_ONE_HAND_SWIPE = 33554432;
    public static final int QUALITY_PARTIAL_TOUCH = Integer.MIN_VALUE;
    public static final int QUALITY_PRESSURE_TOO_HARD = 64;
    public static final int QUALITY_PRESSURE_TOO_LIGHT = 32;
    public static final int QUALITY_REVERSE_MOTION = 524288;
    public static final int QUALITY_SKEW_TOO_LARGE = 262144;
    public static final int QUALITY_SOMETHING_ON_THE_SENSOR = 4;
    public static final int QUALITY_STICTION = 16777216;
    public static final int QUALITY_TOO_FAST = 512;
    public static final int QUALITY_TOO_SHORT = 131072;
    public static final int QUALITY_TOO_SLOW = 65536;
    public static final int QUALITY_WATER = 4096;
    public static final int QUALITY_WET_FINGER = 8;
    public static final int RESULT_CANCELED = -2;
    public static final int RESULT_FAILED = -1;
    public static final int RESULT_NO_AUTHORITY = -4;
    public static final int RESULT_OK = 0;
    public static final int RESULT_TOO_MANY_FINGER = -5;
    public static final int RESUME_ENROLL = 2011;
    public static final int SENSOR_EEPROM_WRITE_COMMAND = 2030;
    public static final int SENSOR_OK = 2004;
    public static final int SENSOR_OUT_OF_ORDER = 2006;
    public static final int SENSOR_TEST_NORMALSCAN_COMMAND = 100103;
    public static final int SENSOR_TEST_SNR_FINAL_COMMAND = 100107;
    public static final int SENSOR_TEST_SNR_ORG_COMMAND = 100106;
    public static final int SENSOR_WORKING = 2005;
    public static final String TAG = "FpCsaClientLib_EgisFingerprint";
    private static Context mContext;
    private static Fingerprint.FingerprintEventListener mFingerprintEventListener;
    private static EgisFingerprint mInstance;
    private Map<String, Integer> fingerIndexMap;
    private SparseArray<String> indexMapToFinger;
    private int mEnrollIndex;
    private String mEnrollUserId;
    private ICS1Native mFPNativeBase;
    private final Handler mHandler;
    private boolean mIsEnrollSessionOpen;
    private boolean mIsFilterOn;
    private boolean mIsFingerOrPWValidate;

    public static EgisFingerprint create(Context context) {
        Log.d(TAG, "create()");
        mContext = context;
        if (mInstance == null) {
            Log.d(TAG, "create(), new EgisFingerprint()");
            mInstance = new EgisFingerprint();
        }
        return mInstance;
    }

    private EgisFingerprint() {
        Handler handler = new Handler() { // from class: egis.client.api.EgisFingerprint.1
            @Override // android.os.Handler
            public void handleMessage(Message msg) {
                Log.d(EgisFingerprint.TAG, "mHandler(), meg.what = " + msg.what + ", msg.arg1 = " + msg.arg1);
                switch (msg.what) {
                    case 1000:
                        EgisFingerprint.this.handleFpResult(msg.arg1);
                        break;
                    case 1200:
                        EgisFingerprint.this.handleTinyResult(msg.arg1);
                        break;
                }
            }
        };
        this.mHandler = handler;
        HashMap map = new HashMap();
        this.fingerIndexMap = map;
        map.put("R1", 1);
        this.fingerIndexMap.put("R2", 2);
        this.fingerIndexMap.put("R3", 3);
        this.fingerIndexMap.put("R4", 4);
        this.fingerIndexMap.put("R5", 5);
        this.fingerIndexMap.put("L1", 6);
        this.fingerIndexMap.put("L2", 7);
        this.fingerIndexMap.put("L3", 8);
        this.fingerIndexMap.put("L4", 9);
        this.fingerIndexMap.put("L5", 10);
        SparseArray<String> sparseArray = new SparseArray<>();
        this.indexMapToFinger = sparseArray;
        sparseArray.put(1, "R1");
        this.indexMapToFinger.put(2, "R2");
        this.indexMapToFinger.put(3, "R3");
        this.indexMapToFinger.put(4, "R4");
        this.indexMapToFinger.put(5, "R5");
        this.indexMapToFinger.put(6, "L1");
        this.indexMapToFinger.put(7, "L2");
        this.indexMapToFinger.put(8, "L3");
        this.indexMapToFinger.put(9, "L4");
        this.indexMapToFinger.put(10, "L5");
        this.mFPNativeBase = new FPCS1HidlNative(handler, mContext);
        getVersion();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public void setEventListener(Fingerprint.FingerprintEventListener fingerprintEventListener) {
        Log.d(TAG, "setEventListener()");
        mFingerprintEventListener = fingerprintEventListener;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public String getVersion() {
        String outputVersion;
        String sdkVersion = this.mFPNativeBase.getVersion();
        String[] sdkVersionArray = sdkVersion.split("\\.");
        if (sdkVersionArray.length < 4) {
            Log.e(TAG, "getVersion(), SDK Version length = " + sdkVersionArray.length);
            return "UNKNOW_VERSION";
        }
        if (sdkVersionArray.length == 4) {
            outputVersion = "1.35." + sdkVersionArray[2] + "." + sdkVersionArray[3];
        } else if (sdkVersionArray.length == 5) {
            outputVersion = "1.35." + sdkVersionArray[2] + "." + sdkVersionArray[3] + "." + sdkVersionArray[4];
        } else {
            outputVersion = "UNKNOW_VERSION";
        }
        Log.d(TAG, "getVersion(), MAJOR_VERSION = 1, JAR_VERSION = 35");
        Log.d(TAG, "getVersion(), SDK Version = " + sdkVersion + ", Output Version = " + outputVersion);
        return outputVersion;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int getSensorStatus() {
        Log.d(TAG, "getSensorStatus()");
        return this.mFPNativeBase.getSensorStatus();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int[] getFingerprintIndexList(String userId) {
        Log.d(TAG, "getFingerprintindexList(), userId = " + userId);
        String enrollList = this.mFPNativeBase.getEnrollList(userId);
        Log.d(TAG, "enrollList=" + enrollList);
        if (enrollList == null || enrollList.equals("")) {
            if (enrollList == null) {
                Log.e(TAG, "getFingerprintindexList(),, enrollList == null");
                return null;
            }
            Log.e(TAG, "getFingerprintindexList(), enrollList.equals(\"\") == true");
            return null;
        }
        String[] fingers = fpSplitor(enrollList);
        Arrays.sort(fingers);
        Log.d(TAG, "getFingerprintindexList(), fingers = " + Arrays.toString(fingers));
        int[] fingerIndex = new int[fingers.length];
        for (int i = 0; i < fingerIndex.length; i++) {
            fingerIndex[i] = this.fingerIndexMap.get(fingers[i]).intValue();
            Log.d(TAG, "getFingerprintindexList(), fingerIndex[" + i + "] = " + fingerIndex[i]);
        }
        return fingerIndex;
    }

    private String[] fpSplitor(String fpData) {
        String[] fingerArray;
        Log.d(TAG, "fpSplitor(), fpData = " + fpData);
        if (fpData.equals("")) {
            Log.e(TAG, "fpSplitor(), fpData is null");
            return null;
        }
        if (fpData.contains(";")) {
            fingerArray = fpData.split(";");
        } else {
            fingerArray = new String[]{fpData};
        }
        Log.d(TAG, "fpSplitor(), fingerArray = " + Arrays.toString(fingerArray));
        return fingerArray;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public byte[] getFingerprintId(String userId, int index) {
        Log.d(TAG, "getFingerprintId(), userId = " + userId + ", index = " + index);
        if (userId == null || userId.equals("") || this.indexMapToFinger.get(index) == null) {
            Log.e(TAG, "getFingerprintId(). input parameter error");
            return null;
        }
        String str = this.mFPNativeBase.dataRead("EGISFPID;" + userId + ";" + this.indexMapToFinger.get(index), PASSWORD);
        if (str == null) {
            Log.e(TAG, "getFingerprintId(), data read error");
            return null;
        }
        return str.getBytes();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public String[] getUserIdList() {
        Log.d(TAG, "getUserIdList()");
        return this.mFPNativeBase.getUserIdList();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int getEnrollRepeatCount() {
        Log.d(TAG, "getEnrollRepeatCount()");
        int[] enrollStatus = this.mFPNativeBase.getEnrollStatus();
        if (enrollStatus[0] != 0 || enrollStatus[1] != 0 || enrollStatus[2] != 0) {
            Log.d(TAG, "getEnrollRepeatCount(), " + enrollStatus[0] + ", " + enrollStatus[1] + ", " + enrollStatus[2]);
            return enrollStatus[0] + enrollStatus[1];
        }
        Log.d(TAG, "getEnrollRepeatCount(), enrollStatus is null");
        return -1;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public String getSensorInfo() {
        Log.d(TAG, "getSensorInfo()");
        return this.mFPNativeBase.getSensorInfo();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int setAccuracyLevel(int level) {
        Log.d(TAG, "setAccuracyLevel(), level = " + level);
        return this.mFPNativeBase.setAccuracyLevel(level);
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int setEnrollSession(boolean flag) {
        Log.d(TAG, "setEnrollSession(), flag = " + flag);
        this.mIsEnrollSessionOpen = flag;
        this.mIsFingerOrPWValidate = false;
        return 0;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int setPassword(String userId, byte[] pwdHash) throws UnsupportedEncodingException {
        Log.d(TAG, "setPassword(), userId = " + userId);
        if (!this.mIsEnrollSessionOpen) {
            Log.e(TAG, "setPassword(), mIsEnrollSessionOpen");
            return -4;
        }
        if (userId.isEmpty()) {
            Log.e(TAG, "setPassword(), userId");
            return -4;
        }
        if (!hasFinger(userId) && !hasPasswd(userId)) {
            this.mIsFingerOrPWValidate = true;
        }
        if (!this.mIsFingerOrPWValidate) {
            Log.e(TAG, "setPassword(), no validate finger");
            return -4;
        }
        boolean ret = this.mFPNativeBase.dataSet("EGISPWD;" + userId, new String(pwdHash, "UTF-8"), PASSWORD);
        if (ret) {
            if (this.mFPNativeBase.doEnrollToDB(userId)) {
                Log.d(TAG, "setPassword(), save dataSet = EGISFPID;" + userId + ";" + this.indexMapToFinger.get(this.mEnrollIndex));
                this.mFPNativeBase.dataSet("EGISFPID;" + userId + ";" + this.indexMapToFinger.get(this.mEnrollIndex), UUID.randomUUID().toString(), PASSWORD);
                return 0;
            }
            return 0;
        }
        return -1;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int verifyPassword(String userId, byte[] pwdHash) throws UnsupportedEncodingException {
        Log.d(TAG, "verifyPassword(), userId = " + userId);
        String dbPwd = this.mFPNativeBase.dataRead("EGISPWD;" + userId, PASSWORD);
        if (dbPwd == null) {
            Log.e(TAG, "verifyPassword(), dbPwd");
            return -1;
        }
        String keyInPw = new String(pwdHash, "UTF-8");
        Log.d(TAG, "verifyPassword(), keyInPw = " + keyInPw + " dbPwd = " + dbPwd);
        if (!keyInPw.equals(dbPwd)) {
            return -1;
        }
        this.mIsFingerOrPWValidate = true;
        return 0;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int identify(String userId) {
        Log.d(TAG, "identify(), userId = " + userId);
        if (userId == null || userId.equals("")) {
            Log.d(TAG, "identify(), Invalid userId");
            return -1;
        }
        if (userId == "Test") {
            boolean ret = this.mFPNativeBase.testEnrollmentAndVerification(false);
            if (!ret) {
                return -1;
            }
            return 0;
        }
        this.mIsFilterOn = false;
        boolean ret2 = this.mFPNativeBase.identify(userId);
        if (!ret2) {
            return -1;
        }
        return 0;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int enroll(String userId, int index) {
        Log.d(TAG, "enroll(), userId = " + userId + ", index = " + index);
        if (userId == null || userId.equals("") || this.indexMapToFinger.get(index) == null) {
            Log.d(TAG, "enroll(), Invalid userId or index");
            return -1;
        }
        if (userId == "Test") {
            boolean ret = this.mFPNativeBase.testEnrollmentAndVerification(true);
            if (!ret) {
                return -1;
            }
            return 0;
        }
        if (!this.mIsEnrollSessionOpen) {
            Log.e(TAG, "enroll(), no open enrollSession");
            return -4;
        }
        if (!hasFinger(userId) && !hasPasswd(userId)) {
            this.mIsFingerOrPWValidate = true;
        }
        if (!this.mIsFingerOrPWValidate) {
            Log.e(TAG, "enroll(), no validate finger or password");
            return -4;
        }
        int[] fingerList = getFingerprintIndexList(userId);
        boolean hasID = false;
        if (fingerList != null && fingerList.length >= 5) {
            for (int i : fingerList) {
                if (i == index) {
                    hasID = true;
                }
            }
        } else {
            hasID = true;
        }
        if (!hasID) {
            Log.d(TAG, "enroll(), Too many");
            return -5;
        }
        this.mIsFilterOn = false;
        String egisId = userId + ";" + this.indexMapToFinger.get(index);
        Log.d(TAG, "enroll(), egisId = " + egisId);
        boolean ret2 = this.mFPNativeBase.enroll(egisId);
        if (!ret2) {
            return -1;
        }
        this.mEnrollUserId = userId;
        this.mEnrollIndex = index;
        Log.d(TAG, "enroll(), mEnrollUserId = " + this.mEnrollUserId + ", mEnrollIndex = " + this.mEnrollIndex);
        return 0;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int swipeEnroll(String userId, int index) {
        Log.d(TAG, "swipeEnroll(), userId = " + userId + ", index = " + index);
        if (userId == null || userId.equals("") || this.indexMapToFinger.get(index) == null) {
            Log.d(TAG, "swipeEnroll(), Invalid userId or index");
            return -1;
        }
        if (userId == "Test") {
            boolean ret = this.mFPNativeBase.testEnrollmentAndVerification(true);
            if (!ret) {
                return -1;
            }
            return 0;
        }
        if (!this.mIsEnrollSessionOpen) {
            Log.e(TAG, "swipeEnroll(), no open enrollSession");
            return -4;
        }
        if (!hasFinger(userId) && !hasPasswd(userId)) {
            this.mIsFingerOrPWValidate = true;
        }
        if (!this.mIsFingerOrPWValidate) {
            Log.e(TAG, "swipeEnroll(), no validate finger or password");
            return -4;
        }
        int[] fingerList = getFingerprintIndexList(userId);
        boolean hasID = false;
        if (fingerList != null && fingerList.length >= 5) {
            for (int i : fingerList) {
                if (i == index) {
                    hasID = true;
                }
            }
        } else {
            hasID = true;
        }
        if (!hasID) {
            Log.d(TAG, "swipeEnroll(), Too many");
            return -5;
        }
        this.mIsFilterOn = false;
        String egisId = userId + ";" + this.indexMapToFinger.get(index);
        Log.d(TAG, "swipeEnroll(), egisId = " + egisId);
        boolean ret2 = this.mFPNativeBase.swipeEnroll(egisId);
        if (!ret2) {
            return -1;
        }
        this.mEnrollUserId = userId;
        this.mEnrollIndex = index;
        Log.d(TAG, "swipeEnroll(), mEnrollUserId = " + this.mEnrollUserId + ", mEnrollIndex = " + this.mEnrollIndex);
        return 0;
    }

    private boolean hasFinger(String userId) {
        Log.d(TAG, "hasFinger(), userId = " + userId);
        String enrollList = this.mFPNativeBase.getEnrollList(userId);
        Log.d(TAG, "hasFinger(), enrollList = " + enrollList);
        return (enrollList == null || enrollList.equals("")) ? false : true;
    }

    private boolean hasPasswd(String userId) {
        Log.d(TAG, "hasPasswd(), userId = " + userId);
        if (this.mFPNativeBase.dataRead("EGISPWD;" + userId, PASSWORD) == null) {
            Log.e(TAG, "hasPasswd(), dataRead false");
            return false;
        }
        return true;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int remove(String userId, int index) {
        Log.d(TAG, "remove(), userId = " + userId + "index = " + index);
        if (userId == null || userId.equals("") || this.indexMapToFinger.get(index) == null) {
            Log.e(TAG, "remove(), Invalid userId");
            return -1;
        }
        if (!this.mIsEnrollSessionOpen) {
            Log.e(TAG, "remove(), no open enrollSession");
            return -4;
        }
        if (!hasFinger(userId) && !hasPasswd(userId)) {
            this.mIsFingerOrPWValidate = true;
        }
        if (!this.mIsFingerOrPWValidate) {
            Log.e(TAG, "remove(), no validate finger or password");
            return -4;
        }
        if (!hasFinger(userId)) {
            Log.e(TAG, "remove(), hasFinger()");
            return -1;
        }
        String egisEnrollId = userId + ";" + this.indexMapToFinger.get(index);
        if (!this.mFPNativeBase.deleteFeature(egisEnrollId)) {
            Log.e(TAG, "remove(), deleteFeature()");
            return -1;
        }
        this.mFPNativeBase.dataDelete("EGISFPID;" + userId + ";" + this.indexMapToFinger.get(index), PASSWORD);
        String enrollList = this.mFPNativeBase.getEnrollList(userId);
        Log.d(TAG, "remove(), enrollList = " + enrollList);
        if (enrollList == null || enrollList.equals("")) {
            Log.d(TAG, "remove(), no finger, so delete password");
            this.mFPNativeBase.dataDelete("EGISPWD;" + userId, PASSWORD);
            return 0;
        }
        return 0;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int request(int status, Object obj) {
        Log.d(TAG, "request(), status = " + status);
        return this.mFPNativeBase.sensorControl(status, 0);
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int verifySensorState(int cmd, int sId, int opt, int logOpt, int uId) {
        Log.d(TAG, "verifySensorState(), cmd = " + cmd + ", opt = " + opt);
        return this.mFPNativeBase.sensorControl(cmd, opt);
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int cancel() {
        Log.d(TAG, "cancel()");
        boolean ret = this.mFPNativeBase.abort();
        if (ret) {
            return 0;
        }
        return -1;
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int cleanup() {
        Log.d(TAG, "cleanup()");
        mContext = null;
        mInstance = null;
        return this.mFPNativeBase.cleanup();
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int enableSensorDevice(boolean enable) {
        Log.d(TAG, "enableSensorDevice(), enable = " + enable);
        int ret = this.mFPNativeBase.sensorDeviceEnable(enable);
        Log.d(TAG, "enableSensorDevice(), ret = " + ret);
        return ret;
    }

    private void notifyOnEnrollStatus() {
        if (mFingerprintEventListener != null) {
            int[] enrollInfo = this.mFPNativeBase.getEnrollStatus();
            Fingerprint.EnrollStatus enrollStatus = new Fingerprint.EnrollStatus();
            enrollStatus.successTrial = enrollInfo[0];
            enrollStatus.badTrial = enrollInfo[1];
            enrollStatus.totalTrial = enrollInfo[0] + enrollInfo[1];
            enrollStatus.progress = enrollInfo[2];
            mFingerprintEventListener.onFingerprintEvent(1000, enrollStatus);
            return;
        }
        Log.e(TAG, "notifyOnEnrollStatus(), mFingerprintEventListener");
    }

    private void notifyOnEnrollMap() {
        if (mFingerprintEventListener != null) {
            Fingerprint.EnrollBitmap enrollMap = new Fingerprint.EnrollBitmap();
            int[] mapInfo = this.mFPNativeBase.getTinyMapInfo();
            Log.d(TAG, "notifyOnEnrollMap(), mapInfo[1] = " + mapInfo[1] + ", mapInfo[2] = " + mapInfo[2]);
            if (mapInfo[1] != 256 && mapInfo[2] != 256) {
                return;
            }
            byte[] map = this.mFPNativeBase.getTinyMap();
            for (int index = 0; index < map.length; index++) {
                map[index] = (byte) (map[index] == -1 ? 0 : 255);
            }
            int index2 = mapInfo[1];
            Bitmap bitmap = Bitmap.createBitmap(index2, mapInfo[2], Bitmap.Config.ALPHA_8);
            bitmap.copyPixelsFromBuffer(ByteBuffer.wrap(map));
            enrollMap.enrollMap = bitmap;
            mFingerprintEventListener.onFingerprintEvent(1005, enrollMap);
            return;
        }
        Log.d(TAG, "notifyOnEnrollMap mFingerprintEventListener");
    }

    private void notifyOnBadImage(int quality) {
        Log.d(TAG, "notifyOnBadImage(), quality = " + quality);
        if (mFingerprintEventListener != null) {
            byte[] rawData = this.mFPNativeBase.getMatchedImg();
            int[] rawDataInfo = this.mFPNativeBase.getMatchedImgInfo();
            Fingerprint.FingerprintBitmap fpBitmap = new Fingerprint.FingerprintBitmap();
            fpBitmap.width = rawDataInfo[0];
            fpBitmap.height = rawDataInfo[1];
            fpBitmap.quality = quality;
            if (rawDataInfo[0] != 0 && rawDataInfo[1] != 0) {
                fpBitmap.bitmap = Bitmap.createBitmap(rawDataInfo[0], rawDataInfo[1], Bitmap.Config.ALPHA_8);
            }
            if (rawData != null) {
                for (int index = 0; index < rawData.length; index++) {
                    rawData[index] = (byte) (~rawData[index]);
                }
                fpBitmap.bitmap.copyPixelsFromBuffer(ByteBuffer.wrap(rawData));
                Log.d(TAG, "rawData len=" + rawData.length);
            }
            mFingerprintEventListener.onFingerprintEvent(1045, fpBitmap);
            return;
        }
        Log.d(TAG, "notifyOnBadImage(), mFingerprintEventListener");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void handleFpResult(int result) {
        switch (result) {
            case 101:
                Log.d(TAG, "handleFpResult(), EEPROM_STATUS_OPERATION_END");
                mFingerprintEventListener.onFingerprintEvent(101, null);
                break;
            case 1001:
                Log.d(TAG, "handleFpResult(), FP_RES_ENROLL_OK");
                if (this.mFPNativeBase.getIsSaveDataSet()) {
                    this.mFPNativeBase.dataSet("EGISFPID;" + this.mEnrollUserId + ";" + this.indexMapToFinger.get(this.mEnrollIndex), UUID.randomUUID().toString(), PASSWORD);
                    this.mFPNativeBase.setIsSaveDataSet(false);
                }
                Fingerprint.FingerprintEventListener fingerprintEventListener = mFingerprintEventListener;
                if (fingerprintEventListener != null) {
                    fingerprintEventListener.onFingerprintEvent(1001, null);
                    Log.i(TAG, "handleFpResult(), ENROLL_SUCCESS");
                }
                this.mEnrollUserId = null;
                break;
            case 1002:
                Log.d(TAG, "handleFpResult(), FP_RES_ENROLL_FAIL");
                Fingerprint.FingerprintEventListener fingerprintEventListener2 = mFingerprintEventListener;
                if (fingerprintEventListener2 != null) {
                    fingerprintEventListener2.onFingerprintEvent(1002, null);
                    Log.i(TAG, "handleFpResult(), ENROLL_FAILED");
                }
                this.mEnrollUserId = null;
                this.mEnrollIndex = 0;
                break;
            case 1003:
                Log.d(TAG, "handleFpResult(), FP_RES_MATCHED_OK");
                this.mIsFingerOrPWValidate = true;
                if (mFingerprintEventListener != null) {
                    Fingerprint.IdentifyResult identifyResult = new Fingerprint.IdentifyResult();
                    String egisId = this.mFPNativeBase.getMatchedUserID();
                    String[] idWithIndex = egisId.split(";");
                    if (idWithIndex.length < 2) {
                        Log.e(TAG, "handleFpResult(), ERROR " + egisId);
                    }
                    Log.d(TAG, "handleFpResult(), user=" + idWithIndex[0] + " index=" + idWithIndex[1]);
                    identifyResult.index = this.fingerIndexMap.get(idWithIndex[1]).intValue();
                    identifyResult.result = 1020;
                    mFingerprintEventListener.onFingerprintEvent(1020, identifyResult);
                    Log.i(TAG, "handleFpResult(), IDENTIFY_SUCCESS");
                }
                break;
            case 1004:
                Log.d(TAG, "handleFpResult(), FP_RES_MATCHED_FAIL");
                if (mFingerprintEventListener != null) {
                    Fingerprint.IdentifyResult identifyResult2 = new Fingerprint.IdentifyResult();
                    identifyResult2.index = -1;
                    identifyResult2.result = 1024;
                    mFingerprintEventListener.onFingerprintEvent(1021, identifyResult2);
                    Log.i(TAG, "handleFpResult(), IDENTIFY_FAILED");
                }
                break;
            case 1008:
                Log.d(TAG, "handleFpResult(), FP_RES_GETTED_GOOD_IMAGE");
                if (mFingerprintEventListener != null) {
                    byte[] rawData = this.mFPNativeBase.getMatchedImg();
                    int[] rawDataInfo = this.mFPNativeBase.getMatchedImgInfo();
                    Fingerprint.FingerprintBitmap fpBitmap = new Fingerprint.FingerprintBitmap();
                    fpBitmap.width = rawDataInfo[0];
                    fpBitmap.height = rawDataInfo[1];
                    fpBitmap.quality = 0;
                    if (rawDataInfo[0] != 0 && rawDataInfo[1] != 0) {
                        fpBitmap.bitmap = Bitmap.createBitmap(rawDataInfo[0], rawDataInfo[1], Bitmap.Config.ALPHA_8);
                    }
                    if (rawData != null) {
                        Log.d(TAG, "handleFpResult(), rawData len = " + rawData.length);
                        for (int index = 0; index < rawData.length; index++) {
                            rawData[index] = (byte) (~rawData[index]);
                        }
                        fpBitmap.bitmap.copyPixelsFromBuffer(ByteBuffer.wrap(rawData));
                    }
                    mFingerprintEventListener.onFingerprintEvent(1044, fpBitmap);
                }
                break;
            case 1009:
                Log.d(TAG, "handleFpResult(), FP_RES_GETTED_BAD_IMAGE");
                notifyOnBadImage(268435456);
                break;
            case 1011:
                Log.d(TAG, "handleFpResult(), FP_RES_ENROLL_COUNT");
                notifyOnEnrollStatus();
                break;
            case 1012:
                Log.d(TAG, "handleFpResult(), FP_RES_ABORT_OK");
                if (!this.mIsFilterOn) {
                    switch (this.mFPNativeBase.getOperationType()) {
                        case 101:
                            mFingerprintEventListener.onFingerprintEvent(1003, null);
                            break;
                        case 102:
                            Fingerprint.IdentifyResult identifyResult3 = new Fingerprint.IdentifyResult();
                            identifyResult3.result = 1022;
                            mFingerprintEventListener.onFingerprintEvent(1021, identifyResult3);
                            Log.i(TAG, "handleFpResult(), IDENTIFY_FAILED");
                            break;
                    }
                }
                break;
            case 1073:
                Log.d(TAG, "handleFpResult(), FP_RES_FINGER_DETECTED");
                Fingerprint.FingerprintEventListener fingerprintEventListener3 = mFingerprintEventListener;
                if (fingerprintEventListener3 != null) {
                    fingerprintEventListener3.onFingerprintEvent(1041, null);
                    Log.i(TAG, "handleFpResult(), CAPTURE_STARTED");
                }
                break;
            case 1074:
                Log.d(TAG, "handleFpResult(), FP_RES_FINGER_REMOVED");
                if (mFingerprintEventListener != null && !this.mIsFilterOn && !Fingerprint.m_abort) {
                    mFingerprintEventListener.onFingerprintEvent(1043, null);
                    Log.i(TAG, "handleFpResult(), CAPTURE_FINISHED");
                    break;
                }
                break;
            case 1075:
                Log.d(TAG, "handleFpResult(), FP_RES_FINGER_WAIT_FPON");
                Fingerprint.FingerprintEventListener fingerprintEventListener4 = mFingerprintEventListener;
                if (fingerprintEventListener4 != null && !this.mIsFilterOn) {
                    fingerprintEventListener4.onFingerprintEvent(1040, null);
                    Log.i(TAG, "handleFpResult(), CAPTURE_READY");
                    break;
                }
                break;
            case 1082:
                Log.d(TAG, "handleFpResult(), FP_RES_PARTIAL_IMG");
                notifyOnBadImage(Integer.MIN_VALUE);
                break;
            case 1084:
                Log.d(TAG, "handleFpResult(), FP_RES_WET_IMG");
                notifyOnBadImage(8);
                break;
            case 1085:
                Log.d(TAG, "handleFpResult(), FP_RES_WATER_IMG");
                notifyOnBadImage(4096);
                break;
            case 1086:
                Log.d(TAG, "handleFpResult(), FP_RES_FAST_IMG");
                notifyOnBadImage(512);
                break;
            case 1087:
                Log.d(TAG, "handleFpResult(), FP_RES_TEST_ENROLL_OK");
                Fingerprint.FingerprintEventListener fingerprintEventListener5 = mFingerprintEventListener;
                if (fingerprintEventListener5 != null) {
                    fingerprintEventListener5.onFingerprintEvent(1001, null);
                    Log.i(TAG, "handleFpResult(), ENROLL_SUCCESS");
                }
                this.mEnrollUserId = null;
                break;
            case 1088:
                Log.d(TAG, "handleFpResult(), FP_RES_TEST_ENROLL_FAIL");
                Fingerprint.FingerprintEventListener fingerprintEventListener6 = mFingerprintEventListener;
                if (fingerprintEventListener6 != null) {
                    fingerprintEventListener6.onFingerprintEvent(1002, null);
                    Log.i(TAG, "handleFpResult(), ENROLL_FAILED");
                }
                this.mEnrollUserId = null;
                this.mEnrollIndex = 0;
                break;
            case 1089:
                Log.d(TAG, "handleFpResult(), FP_RES_TEST_MATCHED_OK");
                this.mIsFingerOrPWValidate = true;
                Fingerprint.FingerprintEventListener fingerprintEventListener7 = mFingerprintEventListener;
                if (fingerprintEventListener7 != null) {
                    fingerprintEventListener7.onFingerprintEvent(1020, null);
                    Log.i(TAG, "handleFpResult(), IDENTIFY_SUCCESS");
                }
                break;
            case 1090:
                Log.d(TAG, "handleFpResult(), FP_RES_TEST_MATCHED_FAIL");
                Fingerprint.FingerprintEventListener fingerprintEventListener8 = mFingerprintEventListener;
                if (fingerprintEventListener8 != null) {
                    fingerprintEventListener8.onFingerprintEvent(1021, null);
                    Log.i(TAG, "handleFpResult(), IDENTIFY_FAILED");
                }
                break;
            case 2020:
                Log.d(TAG, "handleFpResult(), EVT_ERROR");
                mFingerprintEventListener.onFingerprintEvent(2020, null);
                break;
            case 2031:
                Log.d(TAG, "handleFpResult(), FACTORY_WRITE_EEPROM_SCRIPT_START");
                mFingerprintEventListener.onFingerprintEvent(2031, null);
                break;
            case 2032:
                Log.d(TAG, "handleFpResult(), FACTORY_WRITE_EEPROM_SCRIPT_END");
                mFingerprintEventListener.onFingerprintEvent(2032, null);
                break;
            case 285212675:
                Log.d(TAG, "handleFpResult(), FACTORY_TEST_EVT_SNSR_TEST_SCRIPT_START");
                mFingerprintEventListener.onFingerprintEvent(285212675, null);
                break;
            case 285212676:
                Log.d(TAG, "handleFpResult(), FACTORY_TEST_EVT_SNSR_TEST_SCRIPT_END");
                mFingerprintEventListener.onFingerprintEvent(285212676, null);
                break;
            case 285212677:
                Log.d(TAG, "handleFpResult(), FACTORY_TEST_EVT_SNSR_TEST_PUT");
                mFingerprintEventListener.onFingerprintEvent(285212677, null);
                break;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void handleTinyResult(int result) {
        switch (result) {
            case 1234:
                Log.d(TAG, "handleTinyResult(), TINY_STATUS_ENROLL_MAP");
                notifyOnEnrollMap();
                break;
            case 1245:
                Log.d(TAG, "handleTinyResult(), TINY_STATUS_HIGHLY_SIMILAR");
                break;
        }
    }

    @Override // egistec.csa.client.api.IFingerprint
    public int eeprom_test(int cmd, int address, int value) {
        Log.d(TAG, "eeprom_test(), cmd = " + cmd + ", address = " + address + ", value = " + value);
        return this.mFPNativeBase.eepromTest(cmd, address, value);
    }
}
