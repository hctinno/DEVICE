package com.samsung.android.uwb_extension.factory;

import android.text.TextUtils;
import android.util.Log;
import java.util.HashMap;
import java.util.Map;
import java.util.StringJoiner;

/* JADX INFO: loaded from: classes.dex */
public class UwbFactoryCommand {

    /* JADX WARN: Failed to restore enum class, 'enum' modifier and super class removed */
    /* JADX WARN: Unknown enum class pattern. Please report as an issue! */
    public static class Group {
        private static final /* synthetic */ Group[] $VALUES;
        public static final String TAG = "UwbFactoryCommand.Group";
        public static final Group UWB_0_0_0;
        public static final Group UWB_0_0_1;
        public static final Group UWB_0_0_2;
        public static final Group UWB_0_0_3;
        public static final Group UWB_0_0_4;
        public static final Group UWB_0_0_5;
        public static final Group UWB_0_0_6;
        public static final Group UWB_0_0_7;
        public static final Group UWB_0_0_8;
        public static final Group UWB_0_0_9;
        public static final Group UWB_0_1_1;
        public static final Group UWB_0_1_2;
        public static final Group UWB_0_1_3;
        public static final Group UWB_0_1_4;
        public static final Group UWB_0_1_5;
        public static final Group UWB_0_1_6;
        public static final Group UWB_0_2_0;
        public static final Group UWB_0_2_1;
        public static final Group UWB_0_2_2;
        public static final Group UWB_0_2_3;
        public static final Group UWB_0_2_4;
        public static final Group UWB_0_2_5;
        public static final Group UWB_0_3_0;
        public static final Group UWB_0_4_0;
        public static final Group UWB_0_4_1;
        public static final Group UWB_0_9_0;
        public static final Group UWB_0_9_1;
        public static final Group UWB_1_0_0;
        public static final Group UWB_O_6_0;
        private static final Map<String, Group> cmdMap;
        boolean mIsNested;
        String mName;

        public static Group valueOf(String name) {
            return (Group) Enum.valueOf(Group.class, name);
        }

        public static Group[] values() {
            return (Group[]) $VALUES.clone();
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$Group$1, reason: invalid class name */
        final enum AnonymousClass1 extends Group {
            private AnonymousClass1(String str, int i, String name, boolean isNested) {
                super(str, i, name, isNested);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.Group
            public String getTestCaseId(String data) {
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                return sDataArray[0];
            }
        }

        static {
            AnonymousClass1 anonymousClass1 = new AnonymousClass1("UWB_0_0_0", 0, "0_0_0", true);
            UWB_0_0_0 = anonymousClass1;
            Group group = new Group("UWB_0_0_1", 1, "0_0_1", false);
            UWB_0_0_1 = group;
            Group group2 = new Group("UWB_0_0_2", 2, "0_0_2", false);
            UWB_0_0_2 = group2;
            Group group3 = new Group("UWB_0_0_3", 3, "0_0_3", false);
            UWB_0_0_3 = group3;
            Group group4 = new Group("UWB_0_0_4", 4, "0_0_4", false);
            UWB_0_0_4 = group4;
            Group group5 = new Group("UWB_0_0_5", 5, "0_0_5", false);
            UWB_0_0_5 = group5;
            Group group6 = new Group("UWB_0_0_6", 6, "0_0_6", false);
            UWB_0_0_6 = group6;
            Group group7 = new Group("UWB_0_0_7", 7, "0_0_7", false);
            UWB_0_0_7 = group7;
            Group group8 = new Group("UWB_0_0_8", 8, "0_0_8", false);
            UWB_0_0_8 = group8;
            Group group9 = new Group("UWB_0_0_9", 9, "0_0_9", false);
            UWB_0_0_9 = group9;
            Group group10 = new Group("UWB_0_1_1", 10, "0_1_1", false);
            UWB_0_1_1 = group10;
            Group group11 = new Group("UWB_0_1_2", 11, "0_1_2", false);
            UWB_0_1_2 = group11;
            Group group12 = new Group("UWB_0_1_3", 12, "0_1_3", false);
            UWB_0_1_3 = group12;
            Group group13 = new Group("UWB_0_1_4", 13, "0_1_4", false);
            UWB_0_1_4 = group13;
            Group group14 = new Group("UWB_0_1_5", 14, "0_1_5", false);
            UWB_0_1_5 = group14;
            Group group15 = new Group("UWB_0_1_6", 15, "0_1_6", false);
            UWB_0_1_6 = group15;
            Group group16 = new Group("UWB_0_2_0", 16, "0_2_0", false);
            UWB_0_2_0 = group16;
            Group group17 = new Group("UWB_0_2_1", 17, "0_2_1", false);
            UWB_0_2_1 = group17;
            Group group18 = new Group("UWB_0_2_2", 18, "0_2_2", false);
            UWB_0_2_2 = group18;
            Group group19 = new Group("UWB_0_2_3", 19, "0_2_3", false);
            UWB_0_2_3 = group19;
            Group group20 = new Group("UWB_0_2_4", 20, "0_2_4", false);
            UWB_0_2_4 = group20;
            Group group21 = new Group("UWB_0_2_5", 21, "0_2_5", false);
            UWB_0_2_5 = group21;
            AnonymousClass2 anonymousClass2 = new AnonymousClass2("UWB_0_3_0", 22, "0_3_0", true);
            UWB_0_3_0 = anonymousClass2;
            Group group22 = new Group("UWB_0_4_0", 23, "0_4_0", false);
            UWB_0_4_0 = group22;
            Group group23 = new Group("UWB_0_4_1", 24, "0_4_1", false);
            UWB_0_4_1 = group23;
            Group group24 = new Group("UWB_O_6_0", 25, "0_6_0", false);
            UWB_O_6_0 = group24;
            AnonymousClass3 anonymousClass3 = new AnonymousClass3("UWB_0_9_0", 26, "0_9_0", true);
            UWB_0_9_0 = anonymousClass3;
            Group group25 = new Group("UWB_0_9_1", 27, "0_9_1", false);
            UWB_0_9_1 = group25;
            AnonymousClass4 anonymousClass4 = new AnonymousClass4("UWB_1_0_0", 28, "1_0_0", true);
            UWB_1_0_0 = anonymousClass4;
            $VALUES = new Group[]{anonymousClass1, group, group2, group3, group4, group5, group6, group7, group8, group9, group10, group11, group12, group13, group14, group15, group16, group17, group18, group19, group20, group21, anonymousClass2, group22, group23, group24, anonymousClass3, group25, anonymousClass4};
            cmdMap = new HashMap();
            for (Group v : values()) {
                cmdMap.put(v.getName(), v);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$Group$2, reason: invalid class name */
        final enum AnonymousClass2 extends Group {
            private AnonymousClass2(String str, int i, String name, boolean isNested) {
                super(str, i, name, isNested);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.Group
            public String getTestCaseId(String data) {
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                return sDataArray[0];
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$Group$3, reason: invalid class name */
        final enum AnonymousClass3 extends Group {
            private AnonymousClass3(String str, int i, String name, boolean isNested) {
                super(str, i, name, isNested);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.Group
            public String getTestCaseId(String data) {
                Log.d(Group.TAG, "getTestCaseId: " + getName() + ", data: " + data);
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                return sDataArray[0];
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$Group$4, reason: invalid class name */
        final enum AnonymousClass4 extends Group {
            private AnonymousClass4(String str, int i, String name, boolean isNested) {
                super(str, i, name, isNested);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.Group
            public String getTestCaseId(String data) {
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                return sDataArray[0];
            }
        }

        public static Group find(String groupName) {
            return cmdMap.get(groupName);
        }

        private Group(String str, int i, String name, boolean isNested) {
            super(str, i);
            this.mName = name;
            this.mIsNested = isNested;
        }

        public String getName() {
            return this.mName;
        }

        public String getTestCaseId(String data) {
            return null;
        }
    }

    /* JADX WARN: Failed to restore enum class, 'enum' modifier and super class removed */
    /* JADX WARN: Unknown enum class pattern. Please report as an issue! */
    public static abstract class TestCommand {
        private static final /* synthetic */ TestCommand[] $VALUES;
        private static final String TAG = "UwbFactoryCommand.TestCommand";
        public static final TestCommand UWB_0_0_0_8;
        public static final TestCommand UWB_CAL_RF_PLL;
        public static final TestCommand UWB_CHANGE_GAP_AND_PACKET;
        public static final TestCommand UWB_CHANGE_GAP_AND_PACKET_WITH_FILTER;
        public static final TestCommand UWB_CHECK_ANTENNA_CONNECTION_STATUS;
        public static final TestCommand UWB_COMPARE_AOA_CAL;
        public static final TestCommand UWB_COMPARE_AOA_CAL_VERSION;
        public static final TestCommand UWB_CREATE_AOA_CAL_TO_EFS;
        public static final TestCommand UWB_CUSTOM_RANGING_ON_WITH_INITIATOR;
        public static final TestCommand UWB_CUSTOM_RANGING_STOP;
        public static final TestCommand UWB_CUSTOM_SET_ANTENNA_PHASE_FLIP;
        public static final TestCommand UWB_ESE_BINDING_STATUS;
        public static final TestCommand UWB_ESE_CONNECTIVITY;
        public static final TestCommand UWB_ESE_DO_BIND;
        public static final TestCommand UWB_ESE_LOOPBACK;
        public static final TestCommand UWB_GET_CHIP_INFO;
        public static final TestCommand UWB_GET_ESE_BINDING_COUNT;
        public static final TestCommand UWB_OFF;
        public static final TestCommand UWB_ON;
        public static final TestCommand UWB_OVERWRITE_PHASE_OFFSET;
        public static final TestCommand UWB_RANGING_OFF;
        public static final TestCommand UWB_RANGING_ON;
        public static final TestCommand UWB_RANGING_START;
        public static final TestCommand UWB_READ_ALL_PHASE_OFFSET_FROM_EFS;
        public static final TestCommand UWB_READ_ALL_TX_POWER_FROM_EFS;
        public static final TestCommand UWB_READ_AOA;
        public static final TestCommand UWB_READ_AOA_AND_PDOA;
        public static final TestCommand UWB_READ_FROM_EFS;
        public static final TestCommand UWB_READ_PHASE_OFFSET;
        public static final TestCommand UWB_READ_RSSI;
        public static final TestCommand UWB_RF_LOOPBACK;
        public static final TestCommand UWB_SET_AOA_RANGING_CONFIG;
        public static final TestCommand UWB_SET_CHANNEL;
        public static final TestCommand UWB_SET_PREAMBLE_INDEX;
        public static final TestCommand UWB_SET_RX_ANTENNA;
        public static final TestCommand UWB_SET_STS_PACKET_TYPE;
        public static final TestCommand UWB_SET_TX_ANTENNA;
        public static final TestCommand UWB_SET_TX_CALIBRATED_POWER;
        public static final TestCommand UWB_SET_TX_POWER;
        public static final TestCommand UWB_SET_TX_RX_ANTENNA;
        public static final TestCommand UWB_WRITE_ALL_TX_POWER;
        public static final TestCommand UWB_WRITE_PHASE_OFFSET;
        public static final TestCommand UWB_WRITE_TO_EFS;
        private static Map<String, TestCommand> cmdMap;
        Group mGroup;
        String mKey;
        String mTestId;

        public abstract ParsedMessage process(String str);

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$1, reason: invalid class name */
        final enum AnonymousClass1 extends TestCommand {
            private AnonymousClass1(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(0);
            }
        }

        public static TestCommand valueOf(String name) {
            return (TestCommand) Enum.valueOf(TestCommand.class, name);
        }

        public static TestCommand[] values() {
            return (TestCommand[]) $VALUES.clone();
        }

        /* JADX WARN: Multi-variable type inference failed */
        static {
            AnonymousClass1 anonymousClass1 = new AnonymousClass1("UWB_OFF", 0, Group.UWB_0_0_0, "0");
            UWB_OFF = anonymousClass1;
            AnonymousClass2 anonymousClass2 = new AnonymousClass2("UWB_ON", 1, Group.UWB_0_0_0, "1");
            UWB_ON = anonymousClass2;
            AnonymousClass3 anonymousClass3 = new AnonymousClass3("UWB_CAL_RF_PLL", 2, Group.UWB_0_0_0, "2");
            UWB_CAL_RF_PLL = anonymousClass3;
            AnonymousClass4 anonymousClass4 = new AnonymousClass4("UWB_RANGING_OFF", 3, Group.UWB_0_0_0, "3");
            UWB_RANGING_OFF = anonymousClass4;
            AnonymousClass5 anonymousClass5 = new AnonymousClass5("UWB_RANGING_ON", 4, Group.UWB_0_0_0, "4");
            UWB_RANGING_ON = anonymousClass5;
            AnonymousClass6 anonymousClass6 = new AnonymousClass6("UWB_CREATE_AOA_CAL_TO_EFS", 5, Group.UWB_0_0_0, "5");
            UWB_CREATE_AOA_CAL_TO_EFS = anonymousClass6;
            AnonymousClass7 anonymousClass7 = new AnonymousClass7("UWB_COMPARE_AOA_CAL", 6, Group.UWB_0_0_0, "6");
            UWB_COMPARE_AOA_CAL = anonymousClass7;
            AnonymousClass8 anonymousClass8 = new AnonymousClass8("UWB_COMPARE_AOA_CAL_VERSION", 7, Group.UWB_0_0_0, "7");
            UWB_COMPARE_AOA_CAL_VERSION = anonymousClass8;
            AnonymousClass9 anonymousClass9 = new AnonymousClass9("UWB_0_0_0_8", 8, Group.UWB_0_0_0, "8");
            UWB_0_0_0_8 = anonymousClass9;
            AnonymousClass10 anonymousClass10 = new AnonymousClass10("UWB_CHECK_ANTENNA_CONNECTION_STATUS", 9, Group.UWB_0_0_0, "9");
            UWB_CHECK_ANTENNA_CONNECTION_STATUS = anonymousClass10;
            String str = null;
            AnonymousClass11 anonymousClass11 = new AnonymousClass11("UWB_SET_TX_ANTENNA", 10, Group.UWB_0_0_1, str);
            UWB_SET_TX_ANTENNA = anonymousClass11;
            String str2 = null;
            AnonymousClass12 anonymousClass12 = new AnonymousClass12("UWB_SET_RX_ANTENNA", 11, Group.UWB_0_0_2, str2);
            UWB_SET_RX_ANTENNA = anonymousClass12;
            AnonymousClass13 anonymousClass13 = new AnonymousClass13("UWB_SET_CHANNEL", 12, Group.UWB_0_0_3, str);
            UWB_SET_CHANNEL = anonymousClass13;
            AnonymousClass14 anonymousClass14 = new AnonymousClass14("UWB_CHANGE_GAP_AND_PACKET", 13, Group.UWB_0_0_4, str2);
            UWB_CHANGE_GAP_AND_PACKET = anonymousClass14;
            AnonymousClass15 anonymousClass15 = new AnonymousClass15("UWB_CHANGE_GAP_AND_PACKET_WITH_FILTER", 14, Group.UWB_0_0_5, str);
            UWB_CHANGE_GAP_AND_PACKET_WITH_FILTER = anonymousClass15;
            AnonymousClass16 anonymousClass16 = new AnonymousClass16("UWB_SET_PREAMBLE_INDEX", 15, Group.UWB_0_0_6, 0 == true ? 1 : 0);
            UWB_SET_PREAMBLE_INDEX = anonymousClass16;
            String str3 = null;
            AnonymousClass17 anonymousClass17 = new AnonymousClass17("UWB_SET_AOA_RANGING_CONFIG", 16, Group.UWB_0_0_7, str3);
            UWB_SET_AOA_RANGING_CONFIG = anonymousClass17;
            AnonymousClass18 anonymousClass18 = new AnonymousClass18("UWB_SET_STS_PACKET_TYPE", 17, Group.UWB_0_0_8, 0 == true ? 1 : 0);
            UWB_SET_STS_PACKET_TYPE = anonymousClass18;
            AnonymousClass19 anonymousClass19 = new AnonymousClass19("UWB_RF_LOOPBACK", 18, Group.UWB_0_0_9, str3);
            UWB_RF_LOOPBACK = anonymousClass19;
            AnonymousClass20 anonymousClass20 = new AnonymousClass20("UWB_SET_TX_POWER", 19, Group.UWB_0_1_1, 0 == true ? 1 : 0);
            UWB_SET_TX_POWER = anonymousClass20;
            AnonymousClass21 anonymousClass21 = new AnonymousClass21("UWB_SET_TX_CALIBRATED_POWER", 20, Group.UWB_0_1_2, str3);
            UWB_SET_TX_CALIBRATED_POWER = anonymousClass21;
            AnonymousClass22 anonymousClass22 = new AnonymousClass22("UWB_READ_RSSI", 21, Group.UWB_0_1_3, 0 == true ? 1 : 0);
            UWB_READ_RSSI = anonymousClass22;
            AnonymousClass23 anonymousClass23 = new AnonymousClass23("UWB_RANGING_START", 22, Group.UWB_0_1_4, 0 == true ? 1 : 0);
            UWB_RANGING_START = anonymousClass23;
            String str4 = null;
            AnonymousClass24 anonymousClass24 = new AnonymousClass24("UWB_WRITE_ALL_TX_POWER", 23, Group.UWB_0_1_5, str4);
            UWB_WRITE_ALL_TX_POWER = anonymousClass24;
            AnonymousClass25 anonymousClass25 = new AnonymousClass25("UWB_READ_ALL_TX_POWER_FROM_EFS", 24, Group.UWB_0_1_6, 0 == true ? 1 : 0);
            UWB_READ_ALL_TX_POWER_FROM_EFS = anonymousClass25;
            AnonymousClass26 anonymousClass26 = new AnonymousClass26("UWB_WRITE_TO_EFS", 25, Group.UWB_0_2_0, str4);
            UWB_WRITE_TO_EFS = anonymousClass26;
            AnonymousClass27 anonymousClass27 = new AnonymousClass27("UWB_READ_FROM_EFS", 26, Group.UWB_0_2_1, 0 == true ? 1 : 0);
            UWB_READ_FROM_EFS = anonymousClass27;
            AnonymousClass28 anonymousClass28 = new AnonymousClass28("UWB_WRITE_PHASE_OFFSET", 27, Group.UWB_0_2_2, str4);
            UWB_WRITE_PHASE_OFFSET = anonymousClass28;
            AnonymousClass29 anonymousClass29 = new AnonymousClass29("UWB_READ_PHASE_OFFSET", 28, Group.UWB_0_2_3, 0 == true ? 1 : 0);
            UWB_READ_PHASE_OFFSET = anonymousClass29;
            AnonymousClass30 anonymousClass30 = new AnonymousClass30("UWB_OVERWRITE_PHASE_OFFSET", 29, Group.UWB_0_2_4, 0 == true ? 1 : 0);
            UWB_OVERWRITE_PHASE_OFFSET = anonymousClass30;
            AnonymousClass31 anonymousClass31 = new AnonymousClass31("UWB_READ_ALL_PHASE_OFFSET_FROM_EFS", 30, Group.UWB_0_2_5, null);
            UWB_READ_ALL_PHASE_OFFSET_FROM_EFS = anonymousClass31;
            AnonymousClass32 anonymousClass32 = new AnonymousClass32("UWB_ESE_DO_BIND", 31, Group.UWB_0_3_0, "0");
            UWB_ESE_DO_BIND = anonymousClass32;
            AnonymousClass33 anonymousClass33 = new AnonymousClass33("UWB_ESE_BINDING_STATUS", 32, Group.UWB_0_3_0, "1");
            UWB_ESE_BINDING_STATUS = anonymousClass33;
            AnonymousClass34 anonymousClass34 = new AnonymousClass34("UWB_GET_ESE_BINDING_COUNT", 33, Group.UWB_0_3_0, "2");
            UWB_GET_ESE_BINDING_COUNT = anonymousClass34;
            AnonymousClass35 anonymousClass35 = new AnonymousClass35("UWB_ESE_CONNECTIVITY", 34, Group.UWB_0_3_0, "3");
            UWB_ESE_CONNECTIVITY = anonymousClass35;
            AnonymousClass36 anonymousClass36 = new AnonymousClass36("UWB_ESE_LOOPBACK", 35, Group.UWB_0_3_0, "4");
            UWB_ESE_LOOPBACK = anonymousClass36;
            AnonymousClass37 anonymousClass37 = new AnonymousClass37("UWB_READ_AOA", 36, Group.UWB_0_4_0, 0 == true ? 1 : 0);
            UWB_READ_AOA = anonymousClass37;
            AnonymousClass38 anonymousClass38 = new AnonymousClass38("UWB_READ_AOA_AND_PDOA", 37, Group.UWB_0_4_1, null);
            UWB_READ_AOA_AND_PDOA = anonymousClass38;
            AnonymousClass39 anonymousClass39 = new AnonymousClass39("UWB_SET_TX_RX_ANTENNA", 38, Group.UWB_O_6_0, 0 == true ? 1 : 0);
            UWB_SET_TX_RX_ANTENNA = anonymousClass39;
            AnonymousClass40 anonymousClass40 = new AnonymousClass40("UWB_CUSTOM_RANGING_ON_WITH_INITIATOR", 39, Group.UWB_0_9_0, "0");
            UWB_CUSTOM_RANGING_ON_WITH_INITIATOR = anonymousClass40;
            AnonymousClass41 anonymousClass41 = new AnonymousClass41("UWB_CUSTOM_RANGING_STOP", 40, Group.UWB_0_9_0, "1");
            UWB_CUSTOM_RANGING_STOP = anonymousClass41;
            AnonymousClass42 anonymousClass42 = new AnonymousClass42("UWB_CUSTOM_SET_ANTENNA_PHASE_FLIP", 41, Group.UWB_0_9_1, null);
            UWB_CUSTOM_SET_ANTENNA_PHASE_FLIP = anonymousClass42;
            AnonymousClass43 anonymousClass43 = new AnonymousClass43("UWB_GET_CHIP_INFO", 42, Group.UWB_1_0_0, "0");
            UWB_GET_CHIP_INFO = anonymousClass43;
            $VALUES = new TestCommand[]{anonymousClass1, anonymousClass2, anonymousClass3, anonymousClass4, anonymousClass5, anonymousClass6, anonymousClass7, anonymousClass8, anonymousClass9, anonymousClass10, anonymousClass11, anonymousClass12, anonymousClass13, anonymousClass14, anonymousClass15, anonymousClass16, anonymousClass17, anonymousClass18, anonymousClass19, anonymousClass20, anonymousClass21, anonymousClass22, anonymousClass23, anonymousClass24, anonymousClass25, anonymousClass26, anonymousClass27, anonymousClass28, anonymousClass29, anonymousClass30, anonymousClass31, anonymousClass32, anonymousClass33, anonymousClass34, anonymousClass35, anonymousClass36, anonymousClass37, anonymousClass38, anonymousClass39, anonymousClass40, anonymousClass41, anonymousClass42, anonymousClass43};
            cmdMap = new HashMap();
            for (TestCommand testCommand : values()) {
                cmdMap.put(testCommand.getKey(), testCommand);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$2, reason: invalid class name */
        final enum AnonymousClass2 extends TestCommand {
            private AnonymousClass2(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(1);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$3, reason: invalid class name */
        final enum AnonymousClass3 extends TestCommand {
            private AnonymousClass3(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(2);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$4, reason: invalid class name */
        final enum AnonymousClass4 extends TestCommand {
            private AnonymousClass4(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(3);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$5, reason: invalid class name */
        final enum AnonymousClass5 extends TestCommand {
            private AnonymousClass5(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 2) {
                    return null;
                }
                ParsedMessage response = ParsedMessage.createMessage(4, Integer.valueOf(Integer.parseInt(sDataArray[1])));
                return response;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$6, reason: invalid class name */
        final enum AnonymousClass6 extends TestCommand {
            private AnonymousClass6(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(5);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$7, reason: invalid class name */
        final enum AnonymousClass7 extends TestCommand {
            private AnonymousClass7(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(6);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$8, reason: invalid class name */
        final enum AnonymousClass8 extends TestCommand {
            private AnonymousClass8(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(7);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$9, reason: invalid class name */
        final enum AnonymousClass9 extends TestCommand {
            private AnonymousClass9(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return null;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$10, reason: invalid class name */
        final enum AnonymousClass10 extends TestCommand {
            private AnonymousClass10(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(32);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$11, reason: invalid class name */
        final enum AnonymousClass11 extends TestCommand {
            private AnonymousClass11(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (UwbFactoryConstant.isDeprecatedCommand(data)) {
                    return ParsedMessage.createMessage(UwbFactoryConstant.MSG_TEST_SET_TX_ANTENNA_DEPRECATED, data);
                }
                return ParsedMessage.createMessage(8, data);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$12, reason: invalid class name */
        final enum AnonymousClass12 extends TestCommand {
            private AnonymousClass12(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    return null;
                }
                if (UwbFactoryConstant.isDeprecatedCommand(data)) {
                    ParsedMessage response = ParsedMessage.createMessage(UwbFactoryConstant.MSG_TEST_SET_RX_ANTENNA_DEPRECATED, data);
                    return response;
                }
                ParsedMessage response2 = ParsedMessage.createMessage(9, data);
                return response2;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$13, reason: invalid class name */
        final enum AnonymousClass13 extends TestCommand {
            private AnonymousClass13(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    return null;
                }
                ParsedMessage response = ParsedMessage.createMessage(10, Byte.valueOf(Byte.parseByte(data)));
                return response;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$14, reason: invalid class name */
        final enum AnonymousClass14 extends TestCommand {
            private AnonymousClass14(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 3) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(11, sDataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$15, reason: invalid class name */
        final enum AnonymousClass15 extends TestCommand {
            private AnonymousClass15(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 5) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(12, sDataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$16, reason: invalid class name */
        final enum AnonymousClass16 extends TestCommand {
            private AnonymousClass16(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                return ParsedMessage.createMessage(13, Byte.valueOf(Byte.parseByte(data)));
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$17, reason: invalid class name */
        final enum AnonymousClass17 extends TestCommand {
            private AnonymousClass17(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 5 && sDataArray.length != 6) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(14, sDataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$18, reason: invalid class name */
        final enum AnonymousClass18 extends TestCommand {
            private AnonymousClass18(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                return ParsedMessage.createMessage(15, Byte.valueOf(Byte.parseByte(data)));
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$19, reason: invalid class name */
        final enum AnonymousClass19 extends TestCommand {
            private AnonymousClass19(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                byte loopbackCmd = Byte.parseByte(data);
                if (loopbackCmd >= 5) {
                    Log.e(TestCommand.TAG, "unsupported command");
                    return null;
                }
                return ParsedMessage.createMessage(16, Byte.valueOf(loopbackCmd));
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$20, reason: invalid class name */
        final enum AnonymousClass20 extends TestCommand {
            private AnonymousClass20(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                return ParsedMessage.createMessage(17, Byte.valueOf(Byte.parseByte(data)));
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$21, reason: invalid class name */
        final enum AnonymousClass21 extends TestCommand {
            private AnonymousClass21(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(18);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$22, reason: invalid class name */
        final enum AnonymousClass22 extends TestCommand {
            private AnonymousClass22(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                if (UwbFactoryConstant.isDeprecatedCommand(data)) {
                    return ParsedMessage.createMessage(UwbFactoryConstant.MSG_TEST_READ_RSSI_DEPRECATED, data);
                }
                return ParsedMessage.createMessage(19, data);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$23, reason: invalid class name */
        final enum AnonymousClass23 extends TestCommand {
            private AnonymousClass23(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(20);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$24, reason: invalid class name */
        final enum AnonymousClass24 extends TestCommand {
            private AnonymousClass24(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 4) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(34, sDataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$25, reason: invalid class name */
        final enum AnonymousClass25 extends TestCommand {
            private AnonymousClass25(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(36);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$26, reason: invalid class name */
        final enum AnonymousClass26 extends TestCommand {
            private AnonymousClass26(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data) || data.length() < 7) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] dataArray = {data.substring(0, 5), data.substring(6)};
                return ParsedMessage.createMessage(21, dataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$27, reason: invalid class name */
        final enum AnonymousClass27 extends TestCommand {
            private AnonymousClass27(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                return ParsedMessage.createMessage(22, data);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$28, reason: invalid class name */
        final enum AnonymousClass28 extends TestCommand {
            private AnonymousClass28(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length == 3) {
                    return ParsedMessage.createMessage(23, sDataArray);
                }
                if (sDataArray.length == 4) {
                    String[] arr = {sDataArray[0], new StringJoiner(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR).add(sDataArray[1]).add(sDataArray[2]).toString(), sDataArray[3]};
                    return ParsedMessage.createMessage(23, arr);
                }
                Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                return null;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$29, reason: invalid class name */
        final enum AnonymousClass29 extends TestCommand {
            private AnonymousClass29(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length == 2) {
                    return ParsedMessage.createMessage(24, sDataArray);
                }
                if (sDataArray.length == 3) {
                    String[] arr = {sDataArray[0], new StringJoiner(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR).add(sDataArray[1]).add(sDataArray[2]).toString()};
                    return ParsedMessage.createMessage(24, arr);
                }
                Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                return null;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$30, reason: invalid class name */
        final enum AnonymousClass30 extends TestCommand {
            private AnonymousClass30(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length == 3) {
                    return ParsedMessage.createMessage(33, sDataArray);
                }
                if (sDataArray.length == 4) {
                    String[] arr = {sDataArray[0], new StringJoiner(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR).add(sDataArray[1]).add(sDataArray[2]).toString(), sDataArray[3]};
                    return ParsedMessage.createMessage(33, arr);
                }
                Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                return null;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$31, reason: invalid class name */
        final enum AnonymousClass31 extends TestCommand {
            private AnonymousClass31(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                return ParsedMessage.createMessage(35);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$32, reason: invalid class name */
        final enum AnonymousClass32 extends TestCommand {
            private AnonymousClass32(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(25);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$33, reason: invalid class name */
        final enum AnonymousClass33 extends TestCommand {
            private AnonymousClass33(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(26);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$34, reason: invalid class name */
        final enum AnonymousClass34 extends TestCommand {
            private AnonymousClass34(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(27);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$35, reason: invalid class name */
        final enum AnonymousClass35 extends TestCommand {
            private AnonymousClass35(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(28);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$36, reason: invalid class name */
        final enum AnonymousClass36 extends TestCommand {
            private AnonymousClass36(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 3) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(29, Integer.parseInt(sDataArray[1]), Integer.parseInt(sDataArray[2]));
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$37, reason: invalid class name */
        final enum AnonymousClass37 extends TestCommand {
            private AnonymousClass37(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(UwbFactoryConstant.MSG_NO_RESPONSE);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$38, reason: invalid class name */
        final enum AnonymousClass38 extends TestCommand {
            private AnonymousClass38(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(UwbFactoryConstant.MSG_NO_RESPONSE);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$39, reason: invalid class name */
        final enum AnonymousClass39 extends TestCommand {
            private AnonymousClass39(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    return null;
                }
                ParsedMessage response = ParsedMessage.createMessage(37, data);
                return response;
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$40, reason: invalid class name */
        final enum AnonymousClass40 extends TestCommand {
            private AnonymousClass40(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(UwbFactoryConstant.MSG_CUSTOM_RANGING_ON_WITH_INITIATOR);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$41, reason: invalid class name */
        final enum AnonymousClass41 extends TestCommand {
            private AnonymousClass41(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(UwbFactoryConstant.MSG_CUSTOM_RANGING_STOP);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$42, reason: invalid class name */
        final enum AnonymousClass42 extends TestCommand {
            private AnonymousClass42(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                if (TextUtils.isEmpty(data)) {
                    Log.e(TestCommand.TAG, "empty sData");
                    return null;
                }
                String[] sDataArray = data.split(UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR);
                if (sDataArray.length != 3) {
                    Log.e(TestCommand.TAG, "sDataArray length is " + sDataArray.length);
                    return null;
                }
                return ParsedMessage.createMessage(UwbFactoryConstant.MSG_CUSTOM_SET_ANTENNA_PHASE_FLIP, sDataArray);
            }
        }

        /* JADX INFO: renamed from: com.samsung.android.uwb_extension.factory.UwbFactoryCommand$TestCommand$43, reason: invalid class name */
        final enum AnonymousClass43 extends TestCommand {
            private AnonymousClass43(String str, int i, Group group, String testId) {
                super(str, i, group, testId);
            }

            @Override // com.samsung.android.uwb_extension.factory.UwbFactoryCommand.TestCommand
            public ParsedMessage process(String data) {
                return ParsedMessage.createMessage(30);
            }
        }

        private TestCommand(String str, int i, Group group, String testId) {
            super(str, i);
            this.mGroup = group;
            this.mTestId = testId;
            this.mKey = getKey(group.getName(), this.mTestId);
        }

        private static String getKey(String key, String postfix) {
            if (!TextUtils.isEmpty(postfix)) {
                String returnKey = key + UwbFactoryIntentManager.FACTORY_CMD_SEPARATOR + postfix;
                return returnKey;
            }
            return key;
        }

        public static TestCommand find(String groupName, String data) {
            Group group = Group.find(groupName);
            if (group == null) {
                Log.d(TAG, "Not find group");
                return null;
            }
            String key = getKey(group.getName(), group.getTestCaseId(data));
            return cmdMap.get(key);
        }

        public String getKey() {
            return this.mKey;
        }
    }
}
