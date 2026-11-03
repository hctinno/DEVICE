package com.samsung.android.uwb_extension.factory;

import android.util.Log;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.OpenOption;
import java.nio.file.Paths;
import java.util.Arrays;

/* JADX INFO: loaded from: classes.dex */
public class UwbFactoryConstant {
    public static final int ANTENNA_STATUS_CONNECTED = 1;
    public static final int ANTENNA_STATUS_NOT_CONNECTED = 0;
    public static final String ANT_AOA_LANDSCAPE = "ANT_AOA_LANDSCAPE";
    public static final String ANT_AOA_PORTRAIT = "ANT_AOA_PORTRAIT";
    public static final String AOA_LANDSCAPE = "AOA_LANDSCAPE";
    public static final String AOA_PORTRAIT = "AOA_PORTRAIT";
    public static final byte AOA_RESULT_REQUEST_DISABLE = 0;
    public static final byte AOA_RESULT_REQUEST_ENABLE = 1;
    public static final byte BPRF_PHR_DATA_RATE_6M81 = 1;
    public static final byte BPRF_PHR_DATA_RATE_850K = 0;
    public static final byte CHANNEL_NUMBER_10 = 10;
    public static final byte CHANNEL_NUMBER_12 = 12;
    public static final byte CHANNEL_NUMBER_13 = 13;
    public static final byte CHANNEL_NUMBER_14 = 14;
    public static final byte CHANNEL_NUMBER_5 = 5;
    public static final byte CHANNEL_NUMBER_6 = 6;
    public static final byte CHANNEL_NUMBER_8 = 8;
    public static final byte CHANNEL_NUMBER_9 = 9;
    public static final byte CIR_CAPTURE_MODE_POST_STS_RX1 = 6;
    public static final byte CIR_CAPTURE_MODE_POST_STS_RX2 = 7;
    public static final byte CIR_CAPTURE_MODE_POST_SYNC_RX1 = 4;
    public static final byte CIR_CAPTURE_MODE_POST_SYNC_RX2 = 5;
    public static final byte CIR_CAPTURE_MODE_PRE_STS_RX1 = 2;
    public static final byte CIR_CAPTURE_MODE_PRE_STS_RX2 = 3;
    public static final byte CIR_CAPTURE_MODE_PRE_SYNC_RX1 = 0;
    public static final byte CIR_CAPTURE_MODE_PRE_SYNC_RX2 = 1;
    public static final int DCDC_SCREENING_INVALID = -6;
    public static final byte DEVICE_ROLE_INITIATOR = 1;
    public static final byte DEVICE_ROLE_RESPONDER = 0;
    public static final byte DEVICE_TYPE_CONTROLEE = 0;
    public static final byte DEVICE_TYPE_CONTROLLER = 1;
    public static final byte HOPPING_MODE_DISABLE = 0;
    public static final byte HOPPING_MODE_FIRA_HOPPING_ENABLE = 1;
    public static final byte KEY_ROTATION_DISABLE = 0;
    public static final byte KEY_ROTATION_ENABLE = 1;
    public static final byte KEY_ROTATION_RATE_0 = 0;
    public static final byte KEY_ROTATION_RATE_1 = 1;
    public static final byte KEY_ROTATION_RATE_10 = 10;
    public static final byte KEY_ROTATION_RATE_11 = 11;
    public static final byte KEY_ROTATION_RATE_12 = 12;
    public static final byte KEY_ROTATION_RATE_13 = 13;
    public static final byte KEY_ROTATION_RATE_14 = 14;
    public static final byte KEY_ROTATION_RATE_15 = 15;
    public static final byte KEY_ROTATION_RATE_2 = 2;
    public static final byte KEY_ROTATION_RATE_3 = 3;
    public static final byte KEY_ROTATION_RATE_4 = 4;
    public static final byte KEY_ROTATION_RATE_5 = 5;
    public static final byte KEY_ROTATION_RATE_6 = 6;
    public static final byte KEY_ROTATION_RATE_7 = 7;
    public static final byte KEY_ROTATION_RATE_8 = 8;
    public static final byte KEY_ROTATION_RATE_9 = 9;
    public static final byte MAC_ADDRESS_MODE_2_BYTES = 0;
    public static final byte MAC_ADDRESS_MODE_8_BYTES = 2;
    public static final byte MAC_ADDRESS_MODE_8_BYTES_2_BYTES_HEADER = 1;
    public static final byte MAC_FCS_TYPE_CRC_16 = 0;
    public static final byte MAC_FCS_TYPE_CRC_32 = 1;
    public static final byte MAC_PAYLOAD_ENCRYPTION_ENCRYPTED = 1;
    public static final byte MAC_PAYLOAD_ENCRYPTION_ENCRYPTED_WITH_MHR_OMISSION = 2;
    public static final byte MAC_PAYLOAD_ENCRYPTION_PLAIN_TEXT = 0;
    public static final String METAL1_PATCH2 = "M1:P2";
    public static final String METAL1_PATCH3 = "M1:P3";
    public static final String METAL_1 = "M_1";
    public static final String METAL_1_PATCH_2 = "M_1:P_2";
    public static final String METAL_1_PATCH_3 = "M_1:P_3";
    public static final String METAL_2 = "M_2";
    public static final int MSG_CUSTOM_RANGING_ON_WITH_INITIATOR = 200;
    public static final int MSG_CUSTOM_RANGING_STOP = 201;
    public static final int MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP = 202;
    public static final int MSG_TEST_CAL_RF_PLL = 2;
    public static final int MSG_TEST_CHANGE_GAP_AND_PACKET = 11;
    public static final int MSG_TEST_CHANGE_GAP_AND_PACKET_WITH_FILTER = 12;
    public static final int MSG_TEST_CHECK_ANTENNA_CONNECTION_STATUS = 32;
    public static final int MSG_TEST_COMPARE_AOA_CAL = 6;
    public static final int MSG_TEST_COMPARE_AOA_CAL_VERSION = 7;
    public static final int MSG_TEST_CREATE_AOA_CAL_TO_EFS = 5;
    public static final int MSG_TEST_ESE_CONNECTIVITY = 28;
    public static final int MSG_TEST_ESE_DO_BIND = 25;
    public static final int MSG_TEST_ESE_LOOPBACK = 29;
    public static final int MSG_TEST_GET_CHIP_INFO = 30;
    public static final int MSG_TEST_GET_ESE_BINDING_COUNT = 27;
    public static final int MSG_TEST_GET_ESE_BINDING_STATUS = 26;
    public static final int MSG_TEST_OVERWRITE_PHASE_OFFSET = 33;
    public static final int MSG_TEST_RANGING_OFF = 3;
    public static final int MSG_TEST_RANGING_ON = 4;
    public static final int MSG_TEST_RANGING_START = 20;
    public static final int MSG_TEST_READ_ALL_PHASE_OFFSET_FROM_EFS = 35;
    public static final int MSG_TEST_READ_ALL_TX_POWER_FROM_EFS = 36;
    public static final int MSG_TEST_READ_FROM_EFS = 22;
    public static final int MSG_TEST_READ_PHASE_OFFSET = 24;
    public static final int MSG_TEST_READ_RSSI = 19;
    public static final int MSG_TEST_READ_RSSI_DEPRECATED = 502;
    public static final int MSG_TEST_RF_LOOPBACK = 16;
    public static final int MSG_TEST_SET_AOA_RANGING_CONFIG = 14;
    public static final int MSG_TEST_SET_CHANNEL = 10;
    public static final int MSG_TEST_SET_PREAMBLE_INDEX = 13;
    public static final int MSG_TEST_SET_RX_ANTENNA = 9;
    public static final int MSG_TEST_SET_RX_ANTENNA_DEPRECATED = 501;
    public static final int MSG_TEST_SET_STS_PACKET_TYPE = 15;
    public static final int MSG_TEST_SET_TX_ANTENNA = 8;
    public static final int MSG_TEST_SET_TX_ANTENNA_DEPRECATED = 500;
    public static final int MSG_TEST_SET_TX_CALIBRATED_POWER = 18;
    public static final int MSG_TEST_SET_TX_POWER = 17;
    public static final int MSG_TEST_SET_TX_RX_ANTENNA = 37;
    public static final int MSG_TEST_SKIP_REGULATION = 31;
    public static final int MSG_TEST_UWB_OFF = 0;
    public static final int MSG_TEST_UWB_ON = 1;
    public static final int MSG_TEST_WRITE_ALL_TX_POWER = 34;
    public static final int MSG_TEST_WRITE_PHASE_OFFSET = 23;
    public static final int MSG_TEST_WRITE_TO_EFS = 21;
    public static final byte MULTI_NODE_MODE_MANY_TO_MANY = 2;
    public static final byte MULTI_NODE_MODE_ONE_TO_MANY = 1;
    public static final byte MULTI_NODE_MODE_UNICAST = 0;
    public static final byte NUMBER_OF_CONTROLEES_1 = 1;
    public static final byte NUMBER_OF_CONTROLEES_2 = 2;
    public static final byte NUMBER_OF_CONTROLEES_3 = 3;
    public static final byte NUMBER_OF_CONTROLEES_4 = 4;
    public static final byte NUMBER_OF_CONTROLEES_5 = 5;
    public static final byte NUMBER_OF_CONTROLEES_6 = 6;
    public static final byte NUMBER_OF_CONTROLEES_7 = 7;
    public static final byte NUMBER_OF_CONTROLEES_8 = 8;
    public static final byte NUMBER_OF_STS_SEGMENTS_0 = 0;
    public static final byte NUMBER_OF_STS_SEGMENTS_1 = 1;
    public static final byte NUMBER_OF_STS_SEGMENTS_2 = 2;
    public static final byte NUMBER_OF_STS_SEGMENTS_3 = 3;
    public static final byte NUMBER_OF_STS_SEGMENTS_4 = 4;
    public static final int NUM_OF_PACKETS_10 = 10;
    public static final int NUM_OF_PACKETS_1000 = 1000;
    public static final String PATCH1_PATCH2 = "P1:P2";
    public static final String PATCH1_PATCH3 = "P1:P3";
    public static final String PATCH_1 = "P_1";
    public static final String PATCH_1_PATCH_2 = "P_1:P_2";
    public static final String PATCH_1_PATCH_3 = "P_1:P_3";
    public static final String PATCH_2 = "P_2";
    public static final String PATCH_3 = "P_3";
    public static final String PATH_CALIBRATION_CONFIG_FILE = "/system/etc/libuwb-cal.conf";
    public static final String PATH_CALIBRATION_CONFIG_FILE_IN_EFS = "/efs/sec_efs/uwb_factory/AOA_CAL_DATA";
    public static final String PATH_CH5_AOA_TX_POWER_CAL = "/efs/sec_efs/uwb_factory/5_P_1";
    public static final String PATH_CH5_LANDSCAPE_PDOA_OFFSET = "/efs/sec_efs/uwb_factory/5_landscape";
    public static final String PATH_CH5_PORTRAIT_PDOA_OFFSET = "/efs/sec_efs/uwb_factory/5_portrait";
    public static final String PATH_CH5_RANGING_TX_POWER_CAL = "/efs/sec_efs/uwb_factory/5_M_1";
    public static final String PATH_CH5_VCO_PLL_CAL = "/efs/sec_efs/uwb_factory/5_RF_PLL";
    public static final String PATH_CH9_AOA_TX_POWER_CAL = "/efs/sec_efs/uwb_factory/9_P_1";
    public static final String PATH_CH9_LANDSCAPE_PDOA_OFFSET = "/efs/sec_efs/uwb_factory/9_landscape";
    public static final String PATH_CH9_PORTRAIT_PDOA_OFFSET = "/efs/sec_efs/uwb_factory/9_portrait";
    public static final String PATH_CH9_RANGING_TX_POWER_CAL = "/efs/sec_efs/uwb_factory/9_M_1";
    public static final String PATH_CH9_VCO_PLL_CAL = "/efs/sec_efs/uwb_factory/9_RF_PLL";
    public static final String PATH_DEFAULT = "/efs/sec_efs/uwb_factory/";
    public static final byte PHR_RANGING_BIT_DISABLE = 0;
    public static final byte PHR_RANGING_BIT_ENABLE = 1;
    public static final byte PREAMBLE_CODE_INDEX_10 = 10;
    public static final byte PREAMBLE_CODE_INDEX_11 = 11;
    public static final byte PREAMBLE_CODE_INDEX_12 = 12;
    public static final byte PREAMBLE_CODE_INDEX_25 = 25;
    public static final byte PREAMBLE_CODE_INDEX_26 = 26;
    public static final byte PREAMBLE_CODE_INDEX_27 = 27;
    public static final byte PREAMBLE_CODE_INDEX_28 = 28;
    public static final byte PREAMBLE_CODE_INDEX_29 = 29;
    public static final byte PREAMBLE_CODE_INDEX_30 = 30;
    public static final byte PREAMBLE_CODE_INDEX_31 = 31;
    public static final byte PREAMBLE_CODE_INDEX_32 = 32;
    public static final byte PREAMBLE_CODE_INDEX_9 = 9;
    public static final byte PREAMBLE_DURATION_32_SYMBOLS = 0;
    public static final byte PREAMBLE_DURATION_64_SYMBOLS = 1;
    public static final byte PRF_MODE_BPRF = 0;
    public static final byte PRF_MODE_HPRF_124M8 = 1;
    public static final byte PRF_MODE_HPRF_249M6 = 2;
    public static final String PSDU = "ABCDABCD";
    public static final byte PSDU_DATA_RATE_27M2 = 2;
    public static final byte PSDU_DATA_RATE_31M2 = 3;
    public static final byte PSDU_DATA_RATE_6M81 = 0;
    public static final byte PSDU_DATA_RATE_7M80 = 1;
    public static final byte PSDU_DATA_RATE_850K = 4;
    public static final byte RANDOMIZE_PSDU_DISABLE = 0;
    public static final byte RANDOMIZE_PSDU_ENABLE = 1;
    public static final byte RANGE_DATA_NTF_CONFIG_DISABLE = 0;
    public static final byte RANGE_DATA_NTF_CONFIG_ENABLE = 1;
    public static final byte RANGE_DATA_NTF_CONFIG_ENABLE_PROXIMITY = 2;
    public static final byte RANGING_DEVICE_ROLE_INITIATOR = 1;
    public static final byte RANGING_DEVICE_ROLE_RESPONDER = 0;
    public static final short RANGING_ROUND_CONTROL_CONTROL_MESSAGE = 2;
    public static final short RANGING_ROUND_CONTROL_MEASUREMENT_REPORT_MESSAGE = 128;
    public static final short RANGING_ROUND_CONTROL_RANGING_RESULT_REPORT_MESSAGE = 1;
    public static final byte RANGING_ROUND_USAGE_DS_TWR_DEFERRED_MODE = 2;
    public static final byte RANGING_ROUND_USAGE_DS_TWR_NON_DEFERRED_MODE = 4;
    public static final byte RANGING_ROUND_USAGE_ONE_WAY_RANGING = 0;
    public static final byte RANGING_ROUND_USAGE_SS_TWR_DEFERRED_MODE = 1;
    public static final byte RANGING_ROUND_USAGE_SS_TWR_NON_DEFERRED_MODE = 3;
    public static final byte RANGING_TIME_STRUCT_BLOCK_BASED_SCHEDULING = 1;
    public static final byte RANGING_TIME_STRUCT_INTERVAL_BASED_SCHEDULING = 0;
    public static final byte RESULT_REPORT_CONFIG_AOA_AZIMUTH = 2;
    public static final byte RESULT_REPORT_CONFIG_AOA_ELEVATION = 4;
    public static final byte RESULT_REPORT_CONFIG_AOA_FOM = 8;
    public static final byte RESULT_REPORT_CONFIG_TOF = 1;
    public static final byte RFRAME_CONFIG_SP0 = 0;
    public static final byte RFRAME_CONFIG_SP1 = 1;
    public static final byte RFRAME_CONFIG_SP2 = 2;
    public static final byte RFRAME_CONFIG_SP3 = 3;
    private static final int RMARKER_RXSTART_LOOPBACK = 69;
    public static final int RMARKER_RX_START_0 = 0;
    public static final int RMARKER_RX_START_FOR_LOOPBACK = 69;
    private static final int RMARKER_TXSTART_LOOPBACK = 124000;
    public static final int RMARKER_TX_START_0 = 0;
    public static final int RMARKER_TX_START_FOR_LOOPBACK = 124000;
    public static final byte RSSI_CALIB_OPTION_LV1 = 0;
    public static final byte RSSI_CALIB_OPTION_LV2 = 1;
    public static final int RSSI_FILT_CNT_10 = 10;
    public static final String RX1 = "RX1";
    public static final String RX1_RX2 = "RX1:RX2";
    public static final String RX2 = "RX2";
    public static final String RX2_RX1 = "RX2:RX1";
    public static final String RX_ANT_0 = "RX_ANT_0";
    public static final String RX_ANT_1 = "RX_ANT_1";
    public static final String RX_ANT_2 = "RX_ANT_2";
    public static final String RX_ANT_3 = "RX_ANT_3";
    public static final String RX_ANT_4 = "RX_ANT_4";
    public static final byte RX_MODE_DUAL_RX = 0;
    public static final byte RX_MODE_RX1_ONLY = 1;
    public static final byte RX_MODE_RX2_ONLY = 2;
    public static final byte SCHEDULED_MODE_TIME_SCHEDULED_RANGING = 1;
    public static final int SESSION_FOR_DEVICE_TEST_MODE = 0;
    public static final byte SFD_ID_0 = 0;
    public static final byte SFD_ID_1 = 1;
    public static final byte SFD_ID_2 = 2;
    public static final byte SFD_ID_3 = 3;
    public static final byte SFD_ID_4 = 4;
    public static final byte STS_CONFIG_DYNAMIC = 1;
    public static final byte STS_CONFIG_DYNAMIC_FOR_RESPONDER_SPECIFIC_SUB_SESSION_KEY = 2;
    public static final byte STS_CONFIG_STATIC = 0;
    public static final byte STS_INDEX_0 = 0;
    public static final byte STS_INDEX_AUTO_INCREMENT_DISABLE = 0;
    public static final byte STS_INDEX_AUTO_INCREMENT_ENABLE = 1;
    public static final byte STS_LENGTH_128_SYMBOLS = 2;
    public static final byte STS_LENGTH_32_SYMBOLS = 0;
    public static final byte STS_LENGTH_64_SYMBOLS = 1;
    public static final byte TEST_SESSION_STS_KEY_OPTION_IEEE_OPTION = 1;
    public static final byte TEST_SESSION_STS_KEY_OPTION_NXP_PROPRIETARY_OPTION = 0;
    public static final byte TOA_MODE_DUAL_RX = 2;
    public static final byte TOA_MODE_RX1_ONLY = 0;
    public static final byte TOA_MODE_RX2_ONLY = 1;
    public static final byte TX_ADAPTIVE_PAYLOAD_POWER_DISABLE = 0;
    public static final byte TX_ADAPTIVE_PAYLOAD_POWER_ENABLE = 1;
    public static final String TX_ANT_0 = "TX_ANT_0";
    public static final String TX_ANT_1 = "TX_ANT_1";
    public static final int T_GAP_2000 = 2000;
    public static final int T_START_450 = 450;
    public static final int T_WIN_750 = 750;
    public static final int VCO_PLL_DONE = 1;
    public static final int VCO_PLL_LOCKING_FAILED = 0;
    public static final int VCO_PLL_NOT_WORKING = -1;
    public static final int VCO_PLL_SAVE_FAILED = -5;
    private static final String TAG = UwbFactoryConstant.class.getSimpleName();
    private static byte DEV_ROLE = 0;
    private static byte DEV_TYPE = 0;
    private static byte RANGING_METHOD = 2;
    private static byte MULTI_NODE_MODE = 0;
    private static byte NO_OF_ANCHORS = 1;
    private static short SRC_MAC_ADDR = 0;
    private static short[] DEST_MAC_ADDR = {1};
    private static short RANGING_INTERVAL = 200;
    private static short SLOT_LEN = 2000;
    private static byte MAC_TYPE = 0;
    private static byte MEAS_REPORT_REQ = 1;
    private static byte AOA_RESULT_REQ = 0;
    private static byte RNG_DATA_NTF = 1;
    private static short RNG_DATA_NTF_PROXIMITY_NEAR = 0;
    private static short RNG_DATA_NTF_PROXIMITY_FAR = 255;
    private static byte RX_MODE = 0;
    private static byte PPDU_CONFIG = 3;
    private static byte NO_OF_SEGMENT = 1;
    private static byte ANTENA_PAIR_SELECTION = 1;
    private static byte TOA_MODE = 2;
    private static byte TX_POWER_ID = 0;
    public static final byte TX_POWER_ID_125 = 125;
    private static byte TX_POWER_ID_LOOPBACK = TX_POWER_ID_125;
    private static byte TX_ADAPTIVE_PAYLOAD = 0;
    private static byte CHANNEL_ID = 9;
    private static byte PREAMBLE_ID = 9;
    private static byte SFD_ID = 0;
    private static byte PSDU_DATA_RATE = 0;
    private static byte PREAMBLE_DURATION = 1;
    private static int NUM_PACKETS = 1000;
    private static int T_GAP = 2000;
    public static final int MSG_NO_RESPONSE = 400;
    private static int T_START = MSG_NO_RESPONSE;
    private static int T_WIN = 1000;
    private static byte RANDOMIZE_PSDU = 0;
    private static byte RAW_PHR = 0;
    private static int RMARKER_TXSTART = 0;
    private static int RMARKER_RXSTART = 0;
    private static byte STS_INDEX_AUTO_INCR = 0;
    private static byte MAC_CONFIG = 0;
    private static int RSSI_FILT_CNT = 1;
    private static byte RSSI_CALIB_OPT = 1;

    public static boolean writeString(String path, Object value) {
        String str;
        StringBuilder sb;
        boolean result = false;
        if (value == null) {
            return false;
        }
        if (!value.getClass().equals(Byte.class) && !value.getClass().equals(Short.class) && !value.getClass().equals(Integer.class) && !value.getClass().equals(Long.class) && !value.getClass().equals(Float.class) && !value.getClass().equals(Double.class) && !value.getClass().equals(String.class)) {
            Log.e(TAG, "Undefined data type");
            return false;
        }
        String data = value.toString();
        FileOutputStream fileOutputStream = null;
        try {
            try {
                fileOutputStream = new FileOutputStream(path);
                fileOutputStream.write(data.getBytes(StandardCharsets.UTF_8));
                fileOutputStream.flush();
                fileOutputStream.getFD().sync();
                fileOutputStream.close();
                Log.d(TAG, "WriteString As " + value.getClass().getSimpleName() + ": path=" + path + ", data=" + data);
                result = true;
                try {
                    fileOutputStream.close();
                } catch (IOException e) {
                    e = e;
                    str = TAG;
                    sb = new StringBuilder();
                    Log.e(str, sb.append("writeString in ").append(path).toString(), e);
                }
            } catch (IOException e2) {
                Log.e(TAG, "writeString in " + path, e2);
                if (fileOutputStream != null) {
                    try {
                        fileOutputStream.close();
                    } catch (IOException e3) {
                        e = e3;
                        str = TAG;
                        sb = new StringBuilder();
                        Log.e(str, sb.append("writeString in ").append(path).toString(), e);
                    }
                }
            }
            return result;
        } catch (Throwable th) {
            if (fileOutputStream != null) {
                try {
                    fileOutputStream.close();
                } catch (IOException e4) {
                    Log.e(TAG, "writeString in " + path, e4);
                }
            }
            throw th;
        }
    }

    public static String readString(String path) throws IOException {
        String str;
        StringBuilder sb;
        String res = null;
        BufferedReader br = null;
        try {
            try {
                File file = new File(path);
                if (file.exists()) {
                    br = new BufferedReader(new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8));
                    res = br.readLine();
                }
                if (br != null) {
                    try {
                    } catch (IOException e) {
                        e = e;
                        str = TAG;
                        sb = new StringBuilder();
                        Log.e(str, sb.append("readString in ").append(path).toString(), e);
                    }
                }
            } finally {
                if (br != null) {
                    try {
                        br.close();
                    } catch (IOException e2) {
                        Log.e(TAG, "readString in " + path, e2);
                    }
                }
            }
        } catch (Exception e3) {
            Log.e(TAG, "readString in " + path, e3);
            if (br != null) {
                try {
                } catch (IOException e4) {
                    e = e4;
                    str = TAG;
                    sb = new StringBuilder();
                    Log.e(str, sb.append("readString in ").append(path).toString(), e);
                }
            }
        }
        return res;
    }

    public static byte readStringAsByte(String path) throws IOException {
        String str = readString(path);
        if (str == null) {
            Log.e(TAG, "readString is NULL");
            return (byte) 0;
        }
        try {
            byte res = Byte.parseByte(str);
            return res;
        } catch (Exception e) {
            e.printStackTrace();
            return (byte) 0;
        }
    }

    public static short readStringAsShort(String path) throws IOException {
        String str = readString(path);
        if (str == null) {
            Log.e(TAG, "readString is NULL");
            return (short) 0;
        }
        try {
            short res = Short.parseShort(str);
            return res;
        } catch (Exception e) {
            e.printStackTrace();
            return (short) 0;
        }
    }

    public static float readStringAsFloat(String path) throws IOException {
        String str = readString(path);
        if (str == null) {
            Log.e(TAG, "readString is NULL");
            return 0.0f;
        }
        try {
            float res = Float.parseFloat(str);
            return res;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
        }
    }

    public static int readStringAsInt(String path) throws IOException {
        String str = readString(path);
        if (str == null) {
            Log.e(TAG, "readString is NULL");
            return 0;
        }
        try {
            int res = Integer.parseInt(str);
            return res;
        } catch (Exception e) {
            e.printStackTrace();
            return 0;
        }
    }

    public static boolean copyFile(String srcPath, String dstPath) {
        boolean result = false;
        try {
            byte[] data = Files.readAllBytes(Paths.get(srcPath, new String[0]));
            Files.write(Paths.get(dstPath, new String[0]), data, new OpenOption[0]);
            result = true;
        } catch (IOException e) {
            Log.w(TAG, "copyFile", e);
        }
        Log.d(TAG, "copyFile src=" + srcPath + ", dst=" + dstPath + ", result: " + result);
        return result;
    }

    public static boolean isFileEquals(String srcPath, String dstPath) {
        try {
            byte[] dataBytesConf = Files.readAllBytes(Paths.get(srcPath, new String[0]));
            byte[] dataBytesEfs = Files.readAllBytes(Paths.get(dstPath, new String[0]));
            boolean result = Arrays.equals(dataBytesConf, dataBytesEfs);
            return result;
        } catch (IOException e) {
            Log.w(TAG, "isFileEquals", e);
            return false;
        }
    }

    public static boolean isFileExists(String filename) {
        File file = new File(filename);
        return file.exists();
    }

    public static boolean isDeprecatedCommand(String ant) {
        if (ant.equals(METAL_1) || ant.equals(PATCH_1) || ant.equals(PATCH_2) || ant.equals(PATCH_3) || ant.equals(METAL_2) || ant.equals(METAL1_PATCH2) || ant.equals(METAL1_PATCH3) || ant.equals(PATCH1_PATCH2) || ant.equals(PATCH1_PATCH3) || ant.equals(METAL_1_PATCH_2) || ant.equals(METAL_1_PATCH_3) || ant.equals(PATCH_1_PATCH_2) || ant.equals(PATCH_1_PATCH_3) || ant.equals(RX1) || ant.equals(RX2) || ant.equals(RX1_RX2) || ant.equals(RX2_RX1)) {
            return true;
        }
        return false;
    }
}
