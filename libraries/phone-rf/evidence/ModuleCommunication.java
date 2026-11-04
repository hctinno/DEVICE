package com.sec.factorymodule.modules;

import android.bluetooth.BluetoothAdapter;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.location.LocationManager;
import android.os.Process;
import android.os.SemSystemProperties;
import androidx.profileinstaller.Encoding$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.ForegroundService$1$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.athandler.AtTemptest$$ExternalSyntheticOutline0;
import com.sec.factorymodule.support.reflection.FileUtilsReflection;
import com.sec.factorymodule.support.reflection.LocationManagerReflection;
import com.sec.xmldata.support.Support$Path;
import com.sec.xmldata.support.XmlUtil;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.util.HashMap;
import java.util.Locale;
import java.util.Timer;
import java.util.TimerTask;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class ModuleCommunication extends ModuleObject {
    public static String BEIDOU_STARTED_PATH = "/data/beidou_started";
    public static String COMBO_BEIDOU_CNO_PATH = "/data/sv_cno_beidou.info";
    public static String COMBO_GLONASS_CNO_PATH = "/data/sv_cno_glonass.info";
    public static final String[] FM_RADIO_TARGET = {"earphone", "speaker"};
    public static String GLONASS_FCN_PATH = "/data/glonass_fcn";
    public static String GLONASS_STARTED_PATH = "/data/glonass_started";
    public static String GPS_CNO_PATH = "/data/sv_cno.info";
    public static String GPS_L5_CNO_PATH = "/data/sv_cno_gps_l5.info";
    public static String GPS_STARTED_PATH = "/data/gps_started";
    public static String LNA_L5_STARTED_PATH = "/data/lna_l5_started";
    public static String LNA_STARTED_PATH = "/data/lna_started";
    public static String SMD_STARTED_PATH = "/data/smd_started";
    public static ModuleCommunication mInstance;
    public boolean isComboMode;
    public boolean isOneCommand;
    public boolean mGpsEnabledByFactory;
    public final AnonymousClass1 mGpsReceiver;
    public final LocationManager mLocationManager;

    /* JADX WARN: Multi-variable type inference failed */
    /* JADX WARN: Type inference failed for: r1v4, types: [android.content.BroadcastReceiver, com.sec.factorymodule.modules.ModuleCommunication$1, java.lang.Object] */
    public ModuleCommunication(Context context) {
        super(context, "ModuleCommunication");
        this.mLocationManager = (LocationManager) getSystemService("location");
        this.isOneCommand = false;
        this.isComboMode = false;
        this.mGpsEnabledByFactory = false;
        ?? r1 = new BroadcastReceiver() { // from class: com.sec.factorymodule.modules.ModuleCommunication.1
            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                if (intent.getAction().equals("com.sec.factory.intent.ACTION_GPS_SERVICE_RESPONSE")) {
                    String stringExtra = intent.getStringExtra("result");
                    AtTemptest$$ExternalSyntheticOutline0.m("ACTION_GPS_SERVICE_RESPONSE result=", stringExtra, ModuleCommunication.this.CLASS_NAME, "mGpsReceiver.onReceive");
                    if ("NG_CN0".equals(stringExtra)) {
                        ModuleCommunication.this.sendResponse("NG_CN0");
                    } else if (!stringExtra.equals("-1")) {
                        ModuleCommunication moduleCommunication = ModuleCommunication.this;
                        if (moduleCommunication.isOneCommand) {
                            moduleCommunication.sendResponse(stringExtra);
                        } else if (!"SMD".equals(ModuleCommunicationService.GPS_MODE)) {
                            ModuleCommunication moduleCommunication2 = ModuleCommunication.this;
                            moduleCommunication2.getClass();
                            Intent intent2 = new Intent("com.android.samsungtest.GPS_OK");
                            intent2.addFlags(16777216);
                            moduleCommunication2.sendBroadcast(intent2);
                        } else if (stringExtra.equals("100")) {
                            ModuleCommunication moduleCommunication3 = ModuleCommunication.this;
                            moduleCommunication3.getClass();
                            Intent intent3 = new Intent("com.android.samsungtest.GPS_OK");
                            intent3.addFlags(16777216);
                            moduleCommunication3.sendBroadcast(intent3);
                        } else {
                            ModuleCommunication.this.sendResponse("OK,".concat(stringExtra));
                        }
                    } else if ("SMD".equals(ModuleCommunicationService.GPS_MODE)) {
                        ModuleCommunication.this.sendResponse("NG");
                    } else {
                        ModuleCommunication.this.sendResponse("NG_TO");
                    }
                    if ("SMD".equals(ModuleCommunicationService.GPS_MODE) || ModuleCommunication.this.isOneCommand) {
                        ModuleCommunication.deleteGpsFiles();
                        ModuleCommunication moduleCommunication4 = ModuleCommunication.this;
                        moduleCommunication4.isOneCommand = false;
                        moduleCommunication4.stopService(new Intent(ModuleCommunication.this.mContext, (Class<?>) ModuleCommunicationService.class));
                    }
                }
            }
        };
        this.mGpsReceiver = r1;
        XmlUtil.log_i(this.CLASS_NAME, "ModuleCommunication", "Create ModuleCommunication");
        if (context.getPackageName().contains("facatfunction")) {
            XmlUtil.log_i(this.CLASS_NAME, "ModuleCommunication", "Init gps files and register Gps Intents");
            GPS_CNO_PATH = "/data/vendor/gps/sv_cno.info";
            GPS_STARTED_PATH = "/data/vendor/gps/gps_started";
            GLONASS_STARTED_PATH = "/data/vendor/gps/glonass_started";
            GLONASS_FCN_PATH = "/data/vendor/gps/glonass_fcn";
            BEIDOU_STARTED_PATH = "/data/vendor/gps/beidou_started";
            COMBO_GLONASS_CNO_PATH = "/data/vendor/gps/sv_cno_glonass.info";
            COMBO_BEIDOU_CNO_PATH = "/data/vendor/gps/sv_cno_beidou.info";
            SMD_STARTED_PATH = "/data/vendor/gps/smd_started";
            LNA_STARTED_PATH = "/data/vendor/gps/lna_started";
            LNA_L5_STARTED_PATH = "/data/vendor/gps/lna_l5_started";
            GPS_L5_CNO_PATH = "/data/vendor/gps/sv_cno_gps_l5.info";
            IntentFilter intentFilter = new IntentFilter("com.sec.factory.intent.ACTION_GPS_SERVICE_RESPONSE");
            XmlUtil.log_d(this.CLASS_NAME, "registerReceiver", "mContext=" + this.mContext + " isExported=true");
            this.mContext.registerReceiver(r1, intentFilter, 2);
            ModuleObject.mRegistedReceiverMap.put(r1, this.mContext);
        }
    }

    public static boolean EthernetState() {
        return SemSystemProperties.get("persist.eth.on", "1").equals("0");
    }

    public static void deleteGpsFiles() {
        try {
            String[] strArr = {GPS_CNO_PATH, GPS_STARTED_PATH, GLONASS_STARTED_PATH, SMD_STARTED_PATH, LNA_STARTED_PATH, LNA_L5_STARTED_PATH, GLONASS_FCN_PATH, BEIDOU_STARTED_PATH, COMBO_GLONASS_CNO_PATH, COMBO_BEIDOU_CNO_PATH, GPS_L5_CNO_PATH};
            for (int i = 0; i < 11; i++) {
                File file = new File(strArr[i]);
                if (file.exists()) {
                    if (file.delete()) {
                        XmlUtil.log_i("ModuleCommunication", "deleteGpsFiles", strArr[i] + " has been deleted.");
                    } else {
                        XmlUtil.log_i("ModuleCommunication", "deleteGpsFiles", "Deleting " + strArr[i] + " is failed. : index : ");
                    }
                }
            }
        } catch (Exception unused) {
            XmlUtil.log_i("ModuleCommunication", "deleteGpsFiles", "Exception");
        }
    }

    public static ModuleCommunication instance(Context context) {
        if (mInstance == null) {
            mInstance = new ModuleCommunication(context);
        }
        return mInstance;
    }

    public final void EthernetSwitch(String str) {
        SemSystemProperties.set("persist.eth.on", str);
        try {
            Thread.sleep(1000L);
            XmlUtil.log_i(this.CLASS_NAME, "EthernetSwitch", "deley MountTime");
        } catch (Exception e) {
            XmlUtil.log_e(e);
        }
    }

    public final void bleSearchStartWithAckOn10s() {
        XmlUtil.log_i(this.CLASS_NAME, "bleSearchStartWithAck", "Start Bluetooth BLE Search timeout=10sec");
        requestActionToBTService(6);
    }

    public final void btActivationWhereAtcmd() {
        boolean zIsEnabled;
        String str = this.CLASS_NAME;
        XmlUtil.log_i(str, "btActivationWhereAtcmd", "Bluetooth Activation where Atcmd");
        if ("Marvell".equalsIgnoreCase(Support$Path.getString("CHIPSET_MANUFACTURE"))) {
            BluetoothAdapter defaultAdapter = BluetoothAdapter.getDefaultAdapter();
            if (defaultAdapter == null) {
                XmlUtil.log_w(str, "isEnabledBtDevice", "mBtAdapter is null");
                zIsEnabled = false;
            } else {
                zIsEnabled = defaultAdapter.isEnabled();
            }
            if (zIsEnabled) {
                new Timer().schedule(new TimerTask() { // from class: com.sec.factorymodule.modules.ModuleCommunication.2
                    @Override // java.util.TimerTask, java.lang.Runnable
                    public final void run() {
                        ModuleCommunication.this.requestActionToBTService(1);
                    }
                }, 600L);
                return;
            }
        }
        requestActionToBTService(1);
    }

    public final void btAntSwitchEdrTxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btAntSwitchEdrTxMid", "btAntSwitchEdrTxMid()");
        requestActionToBTService(81);
    }

    public final void btAudioTestStart() {
        XmlUtil.log_i(this.CLASS_NAME, "btAudioTestStart", "Start Bluetooth Audio Test");
        requestActionToBTService(8);
    }

    public final void btAudioTestStop() {
        XmlUtil.log_i(this.CLASS_NAME, "btAudioTestStop", "Stop Bluetooth Audio Test");
        requestActionToBTService(9);
    }

    public final void btBrRxHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrRxHigh", "btBrRxHigh()");
        requestActionToBTService(45);
    }

    public final void btBrRxLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrRxLow", "btBrRxLow()");
        requestActionToBTService(43);
    }

    public final void btBrRxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrRxMid", "btBrRxMid()");
        requestActionToBTService(44);
    }

    public final void btBrTxHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrTxHigh", "btBrTxHigh()");
        requestActionToBTService(42);
    }

    public final void btBrTxLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrTxLow", "btBrTxLow()");
        requestActionToBTService(40);
    }

    public final void btBrTxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btBrTxMid", "btBrTxMid()");
        requestActionToBTService(41);
    }

    public final void btDeactivation() {
        XmlUtil.log_i(this.CLASS_NAME, "btDeactivation", "Bluetooth Deactivation");
        requestActionToBTService(2);
    }

    public final void btEdrRxHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrRxHigh", "btEdrRxHigh()");
        requestActionToBTService(35);
    }

    public final void btEdrRxLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrRxLow", "btEdrRxLow()");
        requestActionToBTService(33);
    }

    public final void btEdrRxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrRxMid", "btEdrRxMid()");
        requestActionToBTService(34);
    }

    public final void btEdrTxHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrTxHigh", "btEdrTxHigh()");
        requestActionToBTService(32);
    }

    public final void btEdrTxLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrTxLow", "btEdrTxLow()");
        requestActionToBTService(30);
    }

    public final void btEdrTxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btEdrTxMid", "btEdrTxMid()");
        requestActionToBTService(31);
    }

    public final void btHpmHighPath() {
        XmlUtil.log_i(this.CLASS_NAME, "btHpmHighPath", "btHpmHighPath()");
        requestActionToBTService(38);
    }

    public final void btHpmLowPath() {
        XmlUtil.log_i(this.CLASS_NAME, "btHpmLowPath", "btHpmLowPath()");
        requestActionToBTService(37);
    }

    public final void btHpmReadPath() {
        XmlUtil.log_i(this.CLASS_NAME, "btHpmReadPath", "btHpmReadPath()");
        requestActionToBTService(39);
    }

    public final void btLeRxHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeRxHigh", "btLeRxHigh()");
        requestActionToBTService(28);
    }

    public final void btLeRxLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeRxLow", "btLeRxLow()");
        requestActionToBTService(26);
    }

    public final void btLeRxMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeRxMid", "btLeRxMid()");
        requestActionToBTService(27);
    }

    public final void btLeTest1M() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTest1M", "btLeTest1M()");
        requestActionToBTService(46);
    }

    public final void btLeTest2M() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTest2M", "btLeTest2M()");
        requestActionToBTService(47);
    }

    public final void btLeTestEnd() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTestEnd", "btLeTestEnd()");
        requestActionToBTService(29);
    }

    public final void btLeTestRead() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTestRead", "btLeTestRead()");
        requestActionToBTService(48);
    }

    public final void btLeTxCarrierChHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxCarrierChHigh", "btLeTxCarrierChHigh()");
        requestActionToBTService(22);
    }

    public final void btLeTxCarrierChLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxCarrierChLow", "btLeTxCarrierChLow()");
        requestActionToBTService(20);
    }

    public final void btLeTxCarrierChMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxCarrierChLow", "btLeTxCarrierChLow()");
        requestActionToBTService(21);
    }

    public final void btLeTxInBandChHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxInBandChHigh", "btLeTxInBandChHigh()");
        requestActionToBTService(25);
    }

    public final void btLeTxInBandChLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxInBandChLow", "btLeTxInBandChLow()");
        requestActionToBTService(23);
    }

    public final void btLeTxInBandChMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxInBandChMid", "btLeTxInBandChMid()");
        requestActionToBTService(24);
    }

    public final void btLeTxModChHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChMid", "btLeTxModChMid()");
        requestActionToBTService(16);
    }

    public final void btLeTxModChHighAA() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChLowAA", "btLeTxModChLowAA()");
        requestActionToBTService(19);
    }

    public final void btLeTxModChLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChLow", "btLeTxModChLow()");
        requestActionToBTService(14);
    }

    public final void btLeTxModChLowAA() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChLowAA", "btLeTxModChLowAA()");
        requestActionToBTService(17);
    }

    public final void btLeTxModChMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChMid", "btLeTxModChMid()");
        requestActionToBTService(15);
    }

    public final void btLeTxModChMidAA() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxModChLowAA", "btLeTxModChLowAA()");
        requestActionToBTService(18);
    }

    public final void btLeTxOutputChHigh() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxOutputChHigh", "btLeTxOutputChHigh()");
        requestActionToBTService(13);
    }

    public final void btLeTxOutputChLow() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxOutputChLow", "btLeTxOutputChLow()");
        requestActionToBTService(11);
    }

    public final void btLeTxOutputChMid() {
        XmlUtil.log_i(this.CLASS_NAME, "btLeTxOutputChMid", "btLeTxOutputChMid()");
        requestActionToBTService(12);
    }

    public final void btREDRxRSSIRead() {
        XmlUtil.log_i(this.CLASS_NAME, "btREDRxRSSIRead", "Read BT RED RX RSSI");
        requestActionToBTService(50);
    }

    public final void btREDTxCalResultRead() {
        XmlUtil.log_i(this.CLASS_NAME, "btREDTxCalResultRead", "Read BT RED TX Cal result");
        requestActionToBTService(51);
    }

    public final void btRfTestStart() {
        XmlUtil.log_i(this.CLASS_NAME, "btAudioTestStart", "Start Bluetooth RF Test");
        Intent intent = new Intent();
        intent.setClassName("com.sec.android.app.bluetoothagent", "com.sec.android.app.bluetoothagent.BluetoothRfTest");
        intent.setFlags(268435456);
        startActivity(intent);
    }

    public final void btRfTestStop() {
        XmlUtil.log_i(this.CLASS_NAME, "btAudioTestStart", "Stop Bluetooth RF Test");
        Intent intent = new Intent("com.android.samsungtest.BluetoothRfTestOff");
        intent.addFlags(16777216);
        sendBroadcast(intent);
    }

    public final void btSearchStart() {
        XmlUtil.log_i(this.CLASS_NAME, "btSearchStart", "Start Bluetooth Search");
        requestActionToBTService(3);
    }

    public final void btSearchStartWithAck() {
        XmlUtil.log_i(this.CLASS_NAME, "btSearchStartWithAck", "Start Bluetooth Search timeout=10sec");
        requestActionToBTService(4);
    }

    public final void btSearchStop() {
        XmlUtil.log_i(this.CLASS_NAME, "btSearchStop", "Stop Bluetooth Search");
        requestActionToBTService(7);
    }

    public final boolean connectionCheckEthernet(int i) {
        String str;
        if (!EthernetState()) {
            EthernetSwitch("0");
            try {
                Thread.sleep(2000L);
                XmlUtil.log_i(this.CLASS_NAME, "ConnectionCheckEthernet", "deley MountTime");
            } catch (Exception e) {
                XmlUtil.log_e(e);
            }
        }
        if (i != 0) {
            if (i == 1 && (str = Support$Path.read("ETHERNET_CONNECTION", true, true)) != null && str.equals("1")) {
                return true;
            }
        } else if (Support$Path.isExistFileID("ETHERNET_MAC_ADDRESS")) {
            return true;
        }
        return false;
    }

    public final void dualBtAclFrame(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtAclFrame", "dualBtAclFrame()");
        requestActionToBTService(77, i);
    }

    public final void dualBtChannel(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtChannel", "dualBtChannel()");
        requestActionToBTService(72, i);
    }

    public final void dualBtCoreSelect(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtCoreSelect", "dualBtCoreSelect()");
        requestActionToBTService(71, i);
    }

    public final void dualBtDataRate(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtDataRate", "dualBtDataRate()");
        requestActionToBTService(73, i);
    }

    public final void dualBtPaMode(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtPaMode", "dualBtPaMode()");
        requestActionToBTService(75, i);
    }

    public final void dualBtPacketType(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtPacketType", "dualBtPacketType()");
        requestActionToBTService(76, i);
    }

    public final void dualBtRxGoodpacket() {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtRxGoodpacket", "dualBtRxGoodpacket()");
        requestActionToBTService(80);
    }

    public final void dualBtRxStartStop(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtRxStartStop", "dualBtRxStartStop()");
        requestActionToBTService(79, i);
    }

    public final void dualBtSignalSelect(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtSignalSelect", "dualBtSignalSelect()");
        requestActionToBTService(70, i);
    }

    public final void dualBtTxPower(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtTxPower", "dualBtTxPower()");
        requestActionToBTService(74, i);
    }

    public final void dualBtTxStartStop(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "dualBtTxStartStop", "dualBtTxStartStop()");
        requestActionToBTService(78, i);
    }

    public final void felicaInitPassword() {
        String str = this.CLASS_NAME;
        XmlUtil.log_i(str, "felicaIDmRead", "Felica Init Password");
        Intent intent = new Intent("com.samsung.felicalock.FELICA_LOCK_REQUEST");
        intent.addFlags(268435456);
        XmlUtil.log_i(str, "felicaIDmRead", "felicaInitPassword FLAG_RECEIVER_FOREGROUND");
        intent.putExtra("CMD", 1);
        intent.addFlags(16777216);
        this.mContext.sendBroadcast(intent);
    }

    public final void felicaReadPassword() {
        String str = this.CLASS_NAME;
        XmlUtil.log_i(str, "felicaReadPassword", "Felica Read Password");
        Intent intent = new Intent("com.samsung.felicalock.FELICA_LOCK_REQUEST");
        intent.addFlags(268435456);
        XmlUtil.log_i(str, "felicaReadPassword", "felicaReadPassword FLAG_RECEIVER_FOREGROUND");
        intent.putExtra("CMD", 2);
        intent.addFlags(16777216);
        this.mContext.sendBroadcast(intent);
    }

    public final void felicaSetDataNTxWhereAtcmd(int i) {
        Intent intent = new Intent("com.sec.android.app.felicatest.FELICA_SET_EDC");
        intent.putExtra("I_DATA", i);
        intent.addFlags(16777216);
        this.mContext.sendBroadcast(intent);
    }

    public final void finalize() throws Throwable {
        if (this.mContext.getPackageName().contains("facatfunction")) {
            HashMap map = ModuleObject.mRegistedReceiverMap;
            AnonymousClass1 anonymousClass1 = this.mGpsReceiver;
            if (map.containsKey(anonymousClass1)) {
                Context context = (Context) map.get(anonymousClass1);
                XmlUtil.log_d(this.CLASS_NAME, "unregisterReceiver", "mContext=" + context);
                context.unregisterReceiver(anonymousClass1);
                map.remove(anonymousClass1);
            }
        }
        super.finalize();
    }

    public final void fmRadioOn(int i, String str) {
        XmlUtil.log_i(this.CLASS_NAME, "fmRadioOn", ForegroundService$1$$ExternalSyntheticOutline0.m("frequency: ", str));
        Intent intent = new Intent("test.mode.radio.on.freq");
        intent.putExtra("frequency", str);
        intent.putExtra("output", FM_RADIO_TARGET[i]);
        intent.setFlags(268435456);
        startActivity(intent);
    }

    public final void gpsAction(String str) {
        Intent intent = new Intent(this.mContext, (Class<?>) ModuleCommunicationService.class);
        intent.putExtra("action", str);
        startService(intent);
    }

    public final void gpsActivation(int i, boolean z) {
        File file;
        String str = this.CLASS_NAME;
        XmlUtil.log_i(str, "[GPS debug #1]gpsActivation", "GPS Activation - mode(GPS : 1, GLONASS : 0, BEIDOU : 2, GPS_L5 : 3) = " + i + ",  isOneCommand = " + z);
        this.isComboMode = false;
        deleteGpsFiles();
        this.isOneCommand = z;
        if (i == 1) {
            this.isComboMode = true;
            file = new File(GPS_STARTED_PATH);
        } else if (i == 0) {
            file = new File(GLONASS_STARTED_PATH);
        } else {
            file = i == 2 ? new File(BEIDOU_STARTED_PATH) : null;
        }
        if (file == null) {
            XmlUtil.log_i(str, "[GPS debug #1]gpsSmdActivation", "filePath == null");
            return;
        }
        try {
            if (!file.createNewFile()) {
                XmlUtil.log_d(str, "gpsActivation", "createNewFile method is failed.");
            }
            FileUtilsReflection.setPermission(FileUtilsReflection.getField("S_IRWXU") | FileUtilsReflection.getField("S_IRWXG") | FileUtilsReflection.getField("S_IRWXO"), file.toString());
        } catch (IOException e) {
            e.printStackTrace();
        }
        if (LocationManagerReflection.isLocationEnabledForUser(this.mLocationManager, Process.myUserHandle())) {
            this.mGpsEnabledByFactory = false;
            gpsAction("ACTION_GPS_START");
        } else {
            LocationManagerReflection.setLocationEnabledForUser(this.mLocationManager, true, Process.myUserHandle());
            this.mGpsEnabledByFactory = true;
            gpsAction("ACTION_GPS_START_DELAY");
        }
    }

    public final void gpsDeactivation() {
        XmlUtil.log_i(this.CLASS_NAME, "gpsDeactivation", "GPS Deactivation");
        deleteGpsFiles();
        stopService(new Intent(this.mContext, (Class<?>) ModuleCommunicationService.class));
        if (this.mGpsEnabledByFactory) {
            LocationManagerReflection.setLocationEnabledForUser(this.mLocationManager, false, Process.myUserHandle());
            this.mGpsEnabledByFactory = false;
        }
    }

    public final String gpsReadCN(int i) {
        String oneLine;
        if (!this.isComboMode || i == 1) {
            oneLine = readOneLine(GPS_CNO_PATH);
        } else if (i == 0) {
            oneLine = readOneLine(COMBO_GLONASS_CNO_PATH);
        } else if (i == 2) {
            oneLine = readOneLine(COMBO_BEIDOU_CNO_PATH);
        } else {
            oneLine = i == 3 ? readOneLine(GPS_L5_CNO_PATH) : null;
        }
        if (oneLine == null || oneLine.equals("") || "0".equals(oneLine)) {
            oneLine = "NG";
        }
        XmlUtil.log_i(this.CLASS_NAME, "gpsReadCN_SingleChannle", "CNO=".concat(oneLine));
        return oneLine;
    }

    public final void gpsSmdActivation(int i) {
        File file;
        String strM = Encoding$$ExternalSyntheticOutline0.m(i, "GPS SMD Activation- mode(COMMUNICATION_CHECK : 0, LNA_CHECK : 1, LNA_L5_CHECK : 2) = ");
        String str = this.CLASS_NAME;
        XmlUtil.log_i(str, "[GPS debug #1]gpsSmdActivation", strM);
        deleteGpsFiles();
        if (i == 0) {
            file = new File(SMD_STARTED_PATH);
        } else if (i == 1) {
            file = new File(LNA_STARTED_PATH);
        } else {
            file = i == 2 ? new File(LNA_L5_STARTED_PATH) : null;
        }
        if (file == null) {
            XmlUtil.log_i(str, "gpsSmdActivation", "filePath is null");
            return;
        }
        try {
            if (!file.createNewFile()) {
                XmlUtil.log_d(str, "gpsSmdActivation", "createNewFile method is failed.");
            }
            FileUtilsReflection.setPermission(FileUtilsReflection.getField("S_IRWXU") | FileUtilsReflection.getField("S_IRWXG") | FileUtilsReflection.getField("S_IRWXO"), file.toString());
        } catch (IOException e) {
            e.printStackTrace();
        }
        if (LocationManagerReflection.isLocationEnabledForUser(this.mLocationManager, Process.myUserHandle())) {
            this.mGpsEnabledByFactory = false;
            gpsAction("ACTION_SMD_START");
        } else {
            LocationManagerReflection.setLocationEnabledForUser(this.mLocationManager, true, Process.myUserHandle());
            this.mGpsEnabledByFactory = true;
            gpsAction("ACTION_SMD_START_DELAY");
        }
    }

    public final void nfcOff() {
        Intent intent = new Intent(this.mContext, (Class<?>) ModuleCommunicationService.class);
        intent.putExtra("action", "ACTION_NFC_OFF");
        startService(intent);
    }

    public final String readEthernetMac() {
        if (!EthernetState()) {
            EthernetSwitch("0");
        }
        String upperCase = null;
        for (int i = 0; i < 10; i++) {
            upperCase = Support$Path.read("ETHERNET_MAC_ADDRESS", true, true);
            boolean zEquals = "00:00:00:00:00:00".equals(upperCase);
            String str = this.CLASS_NAME;
            if (!zEquals) {
                XmlUtil.log_i(str, "ReadEthernetMac", "Mount Success");
                break;
            }
            try {
                Thread.sleep(500L);
                XmlUtil.log_i(str, "ReadEthernetMac", "deley MountTime");
            } catch (Exception e) {
                XmlUtil.log_e(e);
            }
        }
        if (upperCase != null) {
            upperCase = upperCase.replaceAll(":", "").toUpperCase(Locale.ENGLISH);
        }
        return (upperCase == null || upperCase.equals("") || !upperCase.equals(Support$Path.read("ETHERNET_MAC_ADDRESS_EFS", true, true))) ? "NG" : upperCase;
    }

    public final String readOneLine(String str) {
        String str2 = this.CLASS_NAME;
        String strTrim = "";
        try {
            FileInputStream fileInputStream = new FileInputStream(str);
            try {
                InputStreamReader inputStreamReader = new InputStreamReader(fileInputStream, Charset.defaultCharset());
                try {
                    BufferedReader bufferedReader = new BufferedReader(inputStreamReader, 8096);
                    try {
                        String line = bufferedReader.readLine();
                        if (line != null) {
                            strTrim = line.trim();
                        }
                        bufferedReader.close();
                        inputStreamReader.close();
                        fileInputStream.close();
                        return strTrim;
                    } catch (Throwable th) {
                        try {
                            bufferedReader.close();
                        } catch (Throwable th2) {
                            th.addSuppressed(th2);
                        }
                        throw th;
                    }
                } catch (Throwable th3) {
                    try {
                        inputStreamReader.close();
                    } catch (Throwable th4) {
                        th3.addSuppressed(th4);
                    }
                    throw th3;
                }
            } catch (Throwable th5) {
                try {
                    fileInputStream.close();
                } catch (Throwable th6) {
                    th5.addSuppressed(th6);
                }
                throw th5;
            }
        } catch (FileNotFoundException unused) {
            XmlUtil.log_i(str2, "readOneLine", "FileNotFoundException");
            return strTrim;
        } catch (IOException unused2) {
            XmlUtil.log_i(str2, "readOneLine", "IOException");
            return strTrim;
        }
    }

    public final void requestActionToBTService(int i) {
        XmlUtil.log_i(this.CLASS_NAME, "requestActionToBTService", Encoding$$ExternalSyntheticOutline0.m(i, "Request extra :"));
        Intent intent = new Intent("com.sec.android.app.bluetoothagent.BT_SERVICE_REQUEST");
        intent.putExtra("CMDID", i);
        intent.addFlags(268435456);
        intent.addFlags(16777216);
        intent.setPackage("com.sec.android.app.bluetoothagent");
        sendBroadcast(intent);
    }

    public final void sendResponse(String str) {
        Intent intent = new Intent("com.android.samsungtest.GPS_RESPONSE");
        intent.putExtra("RES", str);
        intent.addFlags(16777216);
        sendBroadcast(intent);
    }

    public final void writeBtId(String str) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < str.length(); i += 2) {
            if (i == str.length() - 2) {
                sb.append(str.substring(i));
            } else {
                sb.append(str.substring(i, i + 2));
                sb.append(":");
            }
        }
        XmlUtil.log_i(this.CLASS_NAME, "writeBtId", "colonadded=" + sb.toString());
        Intent intent = new Intent("com.sec.android.app.bluetoothagent.BT_ID_WRITE");
        intent.putExtra("MAC_DATA", sb.toString());
        intent.addFlags(268435456);
        intent.setPackage("com.sec.android.app.bluetoothagent");
        sendBroadcast(intent);
    }

    public final boolean writeEthernetMac(String str) {
        File file = new File(Support$Path.getFilePath("SECEFS_ETH_DIRECTORY"));
        if (!file.exists()) {
            String str2 = this.CLASS_NAME;
            XmlUtil.log_i(str2, "WriteEthernetMac", "Create ETHERNET_MAC_ADDRESS_EFS directory...");
            if (!file.mkdir()) {
                XmlUtil.log_d(str2, "WriteEthernetMac", "mkdir method is failed.");
            }
            file.setExecutable(true, true);
            if (!file.setWritable(true, true)) {
                XmlUtil.log_d(str2, "WriteEthernetMac", "setWritable method is failed.");
            }
            file.setReadable(true, false);
        }
        boolean zWrite = Support$Path.write("ETHERNET_MAC_ADDRESS_EFS", str.toUpperCase(Locale.ENGLISH));
        if (!zWrite) {
            return zWrite;
        }
        if (!EthernetState()) {
            EthernetSwitch("0");
        }
        try {
            Thread.sleep(1000L);
            SemSystemProperties.set("persist.eth.efuse", "1");
            Thread.sleep(3000L);
            SemSystemProperties.set("persist.eth.efuse", "0");
            if (EthernetState()) {
                EthernetSwitch("1");
            }
            EthernetSwitch("0");
            return zWrite;
        } catch (Exception e) {
            XmlUtil.log_e(e);
            return false;
        }
    }

    public final void writeWifiId(String str) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < str.length(); i += 2) {
            if (i == str.length() - 2) {
                sb.append(str.substring(i));
            } else {
                sb.append(str.substring(i, i + 2));
                sb.append(":");
            }
        }
        Intent intent = new Intent("com.sec.android.app.wlantest.WIFI_ID_WRITE");
        intent.putExtra("MAC_DATA", sb.toString());
        intent.addFlags(268435456);
        intent.addFlags(16777216);
        sendBroadcast(intent);
    }

    public final void requestActionToBTService(int i, int i2) {
        XmlUtil.log_i(this.CLASS_NAME, "requestActionToBTService", Encoding$$ExternalSyntheticOutline0.m(i, "Request extra :"));
        Intent intent = new Intent("com.sec.android.app.bluetoothagent.BT_SERVICE_REQUEST");
        intent.putExtra("CMDID", i);
        intent.putExtra("EXTRA_BT_DATA", i2);
        intent.addFlags(268435456);
        intent.addFlags(16777216);
        intent.setPackage("com.sec.android.app.bluetoothagent");
        sendBroadcast(intent);
    }
}
