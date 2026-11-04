package com.samsung.android.uwb_extension;

import com.samsung.uwb.support.util.UwbUtil;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/* JADX INFO: loaded from: classes.dex */
public class UciBuilder {
    public static final byte EXTENDED_APP_CONFIG_ID = -29;
    private static final String TAG = "UciBuilder";
    public static final byte TEST_CONFIG_ID = -27;
    public static final int UCI_GID_APP_DATA_MANAGE = 9;
    public static final int UCI_GID_CORE = 0;
    public static final int UCI_GID_MASK = 15;
    public static final int UCI_GID_PROPRIETARY = 14;
    public static final int UCI_GID_RANGE_MANAGE = 2;
    public static final int UCI_GID_SESSION_MANAGE = 1;
    public static final int UCI_GID_SHIFT = 0;
    public static final int UCI_GID_TEST = 13;
    public static final int UCI_MAX_PAYLOAD_SIZE = 255;
    public static final int UCI_MSG_HDR_SIZE = 4;
    public static final int UCI_MTS_CMD = 32;
    public static final int UCI_MTS_NTF = 96;
    public static final int UCI_MTS_RSP = 64;
    public static final byte UCI_MT_SHIFT = 5;
    public static final int UCI_NTF_WAIT_TIMEOUT = 4000;
    public static final int UCI_OID_BINDING_STATUS_NTF = 19;
    public static final int UCI_OID_CORE_DEVICE_INIT = 0;
    public static final int UCI_OID_DBG_RFRAME_LOG_NTF = 11;
    public static final int UCI_OID_DO_CALIBRATION = 24;
    public static final int UCI_OID_GET_ALL_UWB_SESSIONS = 15;
    public static final int UCI_OID_GET_CALIBRATION = 18;
    public static final int UCI_OID_MASK = 63;
    public static final int UCI_OID_QUERY_TEMPERATURE = 25;
    public static final byte UCI_OID_RANGE_DATA_NTF = 0;
    public static final int UCI_OID_SCHEDULER_STATUS_NTF = 20;
    public static final byte UCI_OID_SESSION_DEINIT = 1;
    public static final byte UCI_OID_SESSION_GET_APP_CONFIG = 4;
    public static final byte UCI_OID_SESSION_GET_COUNT = 5;
    public static final byte UCI_OID_SESSION_INIT = 0;
    public static final byte UCI_OID_SESSION_SET_APP_CONFIG = 3;
    public static final byte UCI_OID_SESSION_STATUS_NTF = 2;
    public static final int UCI_OID_SET_CALIBRATION = 17;
    public static final int UCI_OID_SE_COMM_DATA_NTF = 26;
    public static final int UCI_OID_SE_COMM_ERROR_NTF = 16;
    public static final int UCI_OID_SE_DO_BIND = 1;
    public static final int UCI_OID_SE_DO_TEST_CONNECTIVITY = 14;
    public static final int UCI_OID_SE_DO_TEST_LOOP = 13;
    public static final int UCI_OID_SE_GET_BINDING_COUNT = 10;
    public static final int UCI_OID_SE_GET_BINDING_STATUS = 12;
    public static final int UCI_OID_SHIFT = 0;
    public static final int UCI_OID_TEST_CLK_DPD_SWITCHING = 41;
    public static final byte UCI_OID_TEST_CONFIG_GET = 1;
    public static final byte UCI_OID_TEST_CONFIG_SET = 0;
    public static final byte UCI_OID_TEST_LOOPBACK = 6;
    public static final byte UCI_OID_TEST_PERIODIC_TX = 2;
    public static final byte UCI_OID_TEST_PER_RX = 3;
    public static final byte UCI_OID_TEST_RX = 5;
    public static final byte UCI_OID_TEST_SS_TWR = 8;
    public static final byte UCI_OID_TEST_STOP_SESSION = 7;
    public static final int UCI_OID_URSK_DELETION_REQ = 36;
    public static final int UCI_OID_UWB_SESSION_KDF_NTF = 21;
    public static final int UCI_OID_UWB_WIFI_COEX_IND_NTF = 22;
    public static final int UCI_OID_UWB_WLAN_COEX_DATA_NTF = 37;
    public static final int UCI_OID_UWB_WLAN_COEX_EXCEPTION_NTF = 38;
    public static final int UCI_OID_UWB_WLAN_UART_CONNECTIVITY_TEST = 27;
    public static final int UCI_OID_WLAN_UWB_IND_ERR_NTF = 23;
    public static final byte UCI_PBF_SHIFT = 4;

    public static byte[] buildSessionInit(int sessionId, byte sessionType) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(5);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(sessionType);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildSessionDeInit(int sessionId) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildSetAppConfig(int sessionId, byte[] appConfigPayload) {
        int payloadLen = appConfigPayload.length + 4;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.put(appConfigPayload);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildSetTestConfig(int sessionId, byte[] testConfigPayload) {
        int payloadLen = testConfigPayload.length + 4;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.put(testConfigPayload);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] getTlvArray(HashMap<String, ByteBuffer> params) {
        ByteBuffer tlvBuffer = ByteBuffer.allocate(2048);
        for (Map.Entry<String, ByteBuffer> entry : params.entrySet()) {
            byte[] tag = UwbUtil.toByteArray(entry.getKey());
            ByteBuffer buffer = entry.getValue();
            buffer.rewind();
            tlvBuffer.put(tag);
            tlvBuffer.put((byte) buffer.capacity());
            tlvBuffer.put(buffer.array());
        }
        byte[] tlvByteArray = new byte[tlvBuffer.position() + 1];
        tlvBuffer.flip();
        tlvByteArray[0] = (byte) params.size();
        tlvBuffer.get(tlvByteArray, 1, tlvByteArray.length - 1);
        return tlvByteArray;
    }

    public static byte[] getTagIdArray(List<String> params) {
        ByteBuffer tlvBuffer = ByteBuffer.allocate(2048);
        for (String tag : params) {
            tlvBuffer.put(UwbUtil.toByteArray(tag));
        }
        byte[] tlvByteArray = new byte[tlvBuffer.position() + 1];
        tlvBuffer.flip();
        tlvByteArray[0] = (byte) params.size();
        tlvBuffer.get(tlvByteArray, 1, tlvByteArray.length - 1);
        return tlvByteArray;
    }

    public static byte[] buildGetAppConfig(int sessionId, byte[] appConfigPayload) {
        int payloadLen = appConfigPayload.length + 4;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.put(appConfigPayload);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetTestConfig(int sessionId, byte[] testConfigPayload) {
        int payloadLen = testConfigPayload.length + 4;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.put(testConfigPayload);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetSessionState(int sessionId) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putInt(sessionId);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildTestPeriodicTx(byte[] psdu) {
        return psdu;
    }

    public static byte[] buildTestStopSession() {
        return new byte[]{0};
    }

    public static byte[] buildSeDoBind() {
        return new byte[]{0};
    }

    public static byte[] buildSeGetBindingStatus() {
        return new byte[]{0};
    }

    public static byte[] buildSeGetBindingCount() {
        return new byte[]{0};
    }

    public static byte[] buildTestSeConnectivity() {
        return new byte[]{0};
    }

    public static byte[] buildTestSeLoop(short count, short milliseconds) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(4);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).putShort(count);
        byteBuffer.putShort(milliseconds);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildSetPdoaOffset(byte channelId, byte type, byte[] value) {
        int payloadLen = value.length + 2;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(channelId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(type);
        byteBuffer.put(value);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetPdoaOffset(byte channelId, byte type) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(2);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(channelId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(type);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildSetAntennaSpacing(byte channelId, byte type, byte[] value) {
        int payloadLen = value.length + 2;
        ByteBuffer byteBuffer = ByteBuffer.allocate(payloadLen);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(channelId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(type);
        byteBuffer.put(value);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetAntennaSpacing(byte channelId, byte type) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(2);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(channelId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(type);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetCalibration(byte channelId, byte type) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(2);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(channelId);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put(type);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }

    public static byte[] buildGetAntennaConnectionStatus() {
        ByteBuffer byteBuffer = ByteBuffer.allocate(1);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN).put((byte) -1);
        byteBuffer.flip();
        byte[] payload = byteBuffer.array();
        return payload;
    }
}
