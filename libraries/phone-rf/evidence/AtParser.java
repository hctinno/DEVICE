package com.sec.facatfunction.aporiented;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.FactoryTest;
import android.os.Looper;
import android.os.SemSystemProperties;
import android.text.TextUtils;
import android.util.Log;
import androidx.lifecycle.LiveData$$ExternalSyntheticOutline0;
import androidx.profileinstaller.ProfileTranscoder$$ExternalSyntheticOutline0;
import com.samsung.android.hardware.secinputdev.SemInputDeviceManager;
import com.samsung.android.nfc.adapter.SamsungNfcAdapter;
import com.sec.facatfunction.aporiented.AtParser$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.DigitizerElectricService$1$$ExternalSyntheticOutline0;
import com.sec.facatfunction.aporiented.ResponseWriter;
import com.sec.facatfunction.aporiented.athandler.AtAcsensor;
import com.sec.facatfunction.aporiented.athandler.AtActtdata;
import com.sec.facatfunction.aporiented.athandler.AtAirpmode;
import com.sec.facatfunction.aporiented.athandler.AtAlertdis;
import com.sec.facatfunction.aporiented.athandler.AtApMemCrc;
import com.sec.facatfunction.aporiented.athandler.AtApchiptt;
import com.sec.facatfunction.aporiented.athandler.AtArpcheck;
import com.sec.facatfunction.aporiented.athandler.AtAutheKey;
import com.sec.facatfunction.aporiented.athandler.AtBaromete;
import com.sec.facatfunction.aporiented.athandler.AtBatttest;
import com.sec.facatfunction.aporiented.athandler.AtBootmode;
import com.sec.facatfunction.aporiented.athandler.AtBrightcn;
import com.sec.facatfunction.aporiented.athandler.AtBtidtest;
import com.sec.facatfunction.aporiented.athandler.AtBtletest;
import com.sec.facatfunction.aporiented.athandler.AtCalidate;
import com.sec.facatfunction.aporiented.athandler.AtChipIdtt;
import com.sec.facatfunction.aporiented.athandler.AtCofpdata;
import com.sec.facatfunction.aporiented.athandler.AtCommandHandler;
import com.sec.facatfunction.aporiented.athandler.AtConntest;
import com.sec.facatfunction.aporiented.athandler.AtControlN;
import com.sec.facatfunction.aporiented.athandler.AtCountrst;
import com.sec.facatfunction.aporiented.athandler.AtCteicode;
import com.sec.facatfunction.aporiented.athandler.AtCtrlpApk;
import com.sec.facatfunction.aporiented.athandler.AtDatasave;
import com.sec.facatfunction.aporiented.athandler.AtDebugLvC;
import com.sec.facatfunction.aporiented.athandler.AtDisptest;
import com.sec.facatfunction.aporiented.athandler.AtEmemtest;
import com.sec.facatfunction.aporiented.athandler.AtEwriteck;
import com.sec.facatfunction.aporiented.athandler.AtFacmtest;
import com.sec.facatfunction.aporiented.athandler.AtFactolog;
import com.sec.facatfunction.aporiented.athandler.AtFactorst;
import com.sec.facatfunction.aporiented.athandler.AtFaildump;
import com.sec.facatfunction.aporiented.athandler.AtFailhist;
import com.sec.facatfunction.aporiented.athandler.AtFcbttest;
import com.sec.facatfunction.aporiented.athandler.AtFceptest;
import com.sec.facatfunction.aporiented.athandler.AtFcfmtest;
import com.sec.facatfunction.aporiented.athandler.AtFeliCaRfCal;
import com.sec.facatfunction.aporiented.athandler.AtFirmvers;
import com.sec.facatfunction.aporiented.athandler.AtFpsensorEgis;
import com.sec.facatfunction.aporiented.athandler.AtFpsensorGoodix;
import com.sec.facatfunction.aporiented.athandler.AtFpsensorQcom;
import com.sec.facatfunction.aporiented.athandler.AtFuelgaic;
import com.sec.facatfunction.aporiented.athandler.AtFunctest;
import com.sec.facatfunction.aporiented.athandler.AtGcamtest;
import com.sec.facatfunction.aporiented.athandler.AtGeomagss;
import com.sec.facatfunction.aporiented.athandler.AtGpsstest;
import com.sec.facatfunction.aporiented.athandler.AtGripsens;
import com.sec.facatfunction.aporiented.athandler.AtGyroscop;
import com.sec.facatfunction.aporiented.athandler.AtHaictest;
import com.sec.facatfunction.aporiented.athandler.AtHeadinfo;
import com.sec.facatfunction.aporiented.athandler.AtHmacmism;
import com.sec.facatfunction.aporiented.athandler.AtHrmosens;
import com.sec.facatfunction.aporiented.athandler.AtHwindick;
import com.sec.facatfunction.aporiented.athandler.AtHwparamd;
import com.sec.facatfunction.aporiented.athandler.AtIdChiptt;
import com.sec.facatfunction.aporiented.athandler.AtIfpmiccn;
import com.sec.facatfunction.aporiented.athandler.AtImemtest;
import com.sec.facatfunction.aporiented.athandler.AtKey;
import com.sec.facatfunction.aporiented.athandler.AtKeyhold;
import com.sec.facatfunction.aporiented.athandler.AtKstringb;
import com.sec.facatfunction.aporiented.athandler.AtLduccsum;
import com.sec.facatfunction.aporiented.athandler.AtLedlampt;
import com.sec.facatfunction.aporiented.athandler.AtLightest;
import com.sec.facatfunction.aporiented.athandler.AtLineinfo;
import com.sec.facatfunction.aporiented.athandler.AtLooptest;
import com.sec.facatfunction.aporiented.athandler.AtNcamtest;
import com.sec.facatfunction.aporiented.athandler.AtNeedcmdt;
import com.sec.facatfunction.aporiented.athandler.AtNfcmtest;
import com.sec.facatfunction.aporiented.athandler.AtOqcsbftt;
import com.sec.facatfunction.aporiented.athandler.AtPdpbacku;
import com.sec.facatfunction.aporiented.athandler.AtPmictest;
import com.sec.facatfunction.aporiented.athandler.AtPowreset;
import com.sec.facatfunction.aporiented.athandler.AtPreconfg;
import com.sec.facatfunction.aporiented.athandler.AtProximit;
import com.sec.facatfunction.aporiented.athandler.AtQuestchk;
import com.sec.facatfunction.aporiented.athandler.AtRamsizec;
import com.sec.facatfunction.aporiented.athandler.AtRapplist;
import com.sec.facatfunction.aporiented.athandler.AtReadRssi;
import com.sec.facatfunction.aporiented.athandler.AtRgbpdisp;
import com.sec.facatfunction.aporiented.athandler.AtRstcompc;
import com.sec.facatfunction.aporiented.athandler.AtRstcount;
import com.sec.facatfunction.aporiented.athandler.AtScampara;
import com.sec.facatfunction.aporiented.athandler.AtSecurebt;
import com.sec.facatfunction.aporiented.athandler.AtSelftest;
import com.sec.facatfunction.aporiented.athandler.AtSensorHb;
import com.sec.facatfunction.aporiented.athandler.AtSerialno;
import com.sec.facatfunction.aporiented.athandler.AtSimdetec;
import com.sec.facatfunction.aporiented.athandler.AtSpecchan;
import com.sec.facatfunction.aporiented.athandler.AtSpkstest;
import com.sec.facatfunction.aporiented.athandler.AtSpkstestNew;
import com.sec.facatfunction.aporiented.athandler.AtSqtPachk;
import com.sec.facatfunction.aporiented.athandler.AtSvcainit;
import com.sec.facatfunction.aporiented.athandler.AtSwdlmode;
import com.sec.facatfunction.aporiented.athandler.AtSysscope;
import com.sec.facatfunction.aporiented.athandler.AtSyssleep;
import com.sec.facatfunction.aporiented.athandler.AtTemptest;
import com.sec.facatfunction.aporiented.athandler.AtTestapku;
import com.sec.facatfunction.aporiented.athandler.AtTjiginfo;
import com.sec.facatfunction.aporiented.athandler.AtTouch;
import com.sec.facatfunction.aporiented.athandler.AtTspptestStandard;
import com.sec.facatfunction.aporiented.athandler.AtTssCheck;
import com.sec.facatfunction.aporiented.athandler.AtUartswit;
import com.sec.facatfunction.aporiented.athandler.AtUbcttest;
import com.sec.facatfunction.aporiented.athandler.AtUencrypt;
import com.sec.facatfunction.aporiented.athandler.AtUsbdebug;
import com.sec.facatfunction.aporiented.athandler.AtUserdata;
import com.sec.facatfunction.aporiented.athandler.AtUwbdtest;
import com.sec.facatfunction.aporiented.athandler.AtVersname;
import com.sec.facatfunction.aporiented.athandler.AtVibrtest;
import com.sec.facatfunction.aporiented.athandler.AtVsimtchk;
import com.sec.facatfunction.aporiented.athandler.AtWColorid;
import com.sec.facatfunction.aporiented.athandler.AtWifiidrw;
import com.sec.facatfunction.aporiented.athandler.AtWifitest;
import com.sec.facatfunction.aporiented.athandler.AtWprotect;
import com.sec.facatfunction.aporiented.athandler.AtZigbtest;
import com.sec.facatfunction.aporiented.athandler.ts.AtLanguset;
import com.sec.facatfunction.aporiented.athandler.ts.AtSwizSkip;
import com.sec.facatfunction.support.FtUtil;
import com.sec.factorymodule.modules.ModuleCommon;
import com.sec.factorymodule.modules.ModuleDevice;
import com.sec.factorymodule.modules.ModulePower;
import com.sec.factorymodule.modules.ModuleSensor;
import com.sec.factorymodule.modules.SensorDeviceInfo;
import com.sec.factorymodule.sensors.SensorProximity;
import com.sec.factorymodule.support.reflection.ContextReflection;
import com.sec.xmldata.support.Element;
import com.sec.xmldata.support.FactoryTestResolver;
import com.sec.xmldata.support.Support$Path;
import com.sec.xmldata.support.XmlUtil;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.OpenOption;
import java.nio.file.Paths;
import java.text.DecimalFormat;
import java.text.NumberFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Locale;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtParser {
    public final HashMap atHandlers;
    public File cmdInfoData;
    public Context mContext;
    public final String[] mFilteredcommandList;
    public final boolean mbExistADC;
    public String mfileName = "CmdInfoData";

    /* JADX WARN: Multi-variable type inference failed */
    public AtParser() {
        ArrayList arrayList;
        String[] strArr;
        synchronized (Support$Path.class) {
            try {
                ArrayList arrayList2 = Support$Path.filteredCommands;
                if (arrayList2 == null) {
                    Support$Path.filteredCommands = new ArrayList();
                    try {
                        for (Element element : FactoryTestResolver.instance().getChildElementSet()) {
                            boolean z = Boolean.parseBoolean(element.getAttribute("enable")) && TextUtils.isEmpty(element.getAttribute("parent_item_id"));
                            String attribute = element.getAttribute("id");
                            if (z && element.getAttribute("tag_type").equals("item-group")) {
                                for (Element element2 : FactoryTestResolver.instance().getChildElementSet("parent_item_id", attribute)) {
                                    String attribute2 = element2.getAttribute("para");
                                    String attribute3 = element2.getAttribute("count");
                                    Support$Path.filteredCommands.add(attribute + "/" + attribute2 + "/" + attribute3);
                                    StringBuilder sb = new StringBuilder();
                                    arrayList = null;
                                    try {
                                        sb.append("filtername-");
                                        sb.append(attribute);
                                        sb.append("/");
                                        sb.append(attribute2);
                                        sb.append("/");
                                        sb.append(attribute3);
                                        XmlUtil.log_d("Support", "CommandFilter", sb.toString());
                                    } catch (Exception e) {
                                        e = e;
                                        e.printStackTrace();
                                        Support$Path.filteredCommands = arrayList;
                                        this.mFilteredcommandList = strArr;
                                        this.mbExistADC = false;
                                        this.atHandlers = new HashMap();
                                        this.mbExistADC = Support$Path.isExistFileID("JIG_CONNECTION_CHECK_ADC");
                                    }
                                }
                            }
                        }
                        arrayList = null;
                        strArr = Support$Path.filteredCommands.isEmpty() ? arrayList : (String[]) Support$Path.filteredCommands.toArray(new String[0]);
                    } catch (Exception e2) {
                        e = e2;
                        arrayList = null;
                    }
                } else {
                    arrayList = null;
                    if (!arrayList2.isEmpty()) {
                        strArr = (String[]) Support$Path.filteredCommands.toArray(new String[0]);
                    }
                }
            } catch (Throwable th) {
                throw th;
            }
        }
        this.mFilteredcommandList = strArr;
        this.mbExistADC = false;
        this.atHandlers = new HashMap();
        this.mbExistADC = Support$Path.isExistFileID("JIG_CONNECTION_CHECK_ADC");
    }

    public static String[] splitArgu(String str) {
        if (!str.contains("=")) {
            return new String[0];
        }
        String strSubstring = str.substring(str.indexOf("=") + 1);
        if (str.contains("BTMLAYER")) {
            return new String[]{strSubstring.substring(0, 1), strSubstring.substring(2, 3), strSubstring.substring(4)};
        }
        String[] strArr = new String[10];
        int i = 0;
        while (strSubstring.contains("\"")) {
            int iIndexOf = strSubstring.indexOf("\"");
            String strSubstring2 = strSubstring.substring(iIndexOf, strSubstring.indexOf("\"", iIndexOf + 1) + 1);
            strSubstring = strSubstring.replace(strSubstring2, "__ARG__" + i);
            FtUtil.log_d("AtParser", "splitArgu()", "subStr : " + strSubstring2 + ", REPLACE : __ARG__" + i + ", args : " + strSubstring);
            strArr[i] = strSubstring2;
            i++;
        }
        String[] strArrSplit = strSubstring.split(",");
        while (true) {
            int i2 = i - 1;
            if (i <= 0 || strArrSplit == null) {
                break;
            }
            for (int i3 = 0; i3 < strArrSplit.length; i3++) {
                if (strArrSplit[i3].equalsIgnoreCase("__ARG__" + i2)) {
                    StringBuilder sb = new StringBuilder("res : ");
                    sb.append(strArrSplit[i3]);
                    sb.append(" : __ARG__");
                    sb.append(i2);
                    sb.append(" : ");
                    AtParser$$ExternalSyntheticOutline0.m(sb, strArr[i2], "AtParser", "splitArgu()");
                    strArrSplit[i3] = strArr[i2];
                    AtParser$$ExternalSyntheticOutline0.m(new StringBuilder("res : "), strArrSplit[i3], "AtParser", "splitArgu()");
                    break;
                }
            }
            i = i2;
        }
        if (strArrSplit != null) {
            StringBuilder sb2 = new StringBuilder("args : ");
            sb2.append(strArrSplit.length);
            sb2.append(" : ");
            AtParser$$ExternalSyntheticOutline0.m(sb2, Arrays.toString(strArrSplit), "AtParser", "splitArgu()");
        }
        return strArrSplit;
    }

    public final boolean isFilteredCommand(String str, String str2) {
        String[] strArrSplitArgu = splitArgu(str);
        String[] strArr = this.mFilteredcommandList;
        if (strArr != null) {
            for (String str3 : strArr) {
                String[] strArrSplit = str3.split("/");
                if (str2.equals(strArrSplit[0])) {
                    String[] strArrSplit2 = strArrSplit[1].split(",");
                    String str4 = strArrSplit[2];
                    int i = 0;
                    while (true) {
                        try {
                            if (i >= Integer.parseInt(str4)) {
                                FtUtil.log_d("AtParser", "isFilteredCommand", AtParser$$ExternalSyntheticOutline0.m("---filtered CMD= ", str3, "  , commandName=", str2));
                                return true;
                            }
                            FtUtil.log_d("AtParser", "compareArgu", "compareArgu : argu[" + i + "]=" + strArrSplitArgu[i] + ", para[" + i + "]=" + strArrSplit2[i]);
                            if (!strArrSplitArgu[i].equals(strArrSplit2[i])) {
                                break;
                            }
                            i++;
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
            }
        }
        return false;
    }

    public final boolean process(String str, ResponseWriter responseWriter) {
        FtUtil.log_d("AtParser", "process", str);
        if (str != null) {
            try {
                if (str.length() >= 1) {
                    if (FactoryTest.isFactoryBinary()) {
                        FtUtil.log_d("AtParser", "process", "Usb Configuration Status = " + Support$Path.read("USB_CONFIG_CHECK", true, true));
                        if (this.mbExistADC) {
                            FtUtil.log_d("AtParser", "process", "Usb ADC Status = " + Support$Path.read("JIG_CONNECTION_CHECK_ADC", true, true));
                        }
                    }
                    if (runCmd(str, responseWriter)) {
                        FtUtil.log_d("AtParser", "process done successfully. cmd = ", str);
                    }
                    return true;
                }
            } catch (StringIndexOutOfBoundsException e) {
                FtUtil.log_e(e);
            }
        }
        return false;
    }

    /* JADX WARN: Code duplicated, block: B:49:0x0b4f  */
    /* JADX WARN: Code duplicated, block: B:69:0x0bb0  */
    /* JADX WARN: Code duplicated, block: B:72:0x0bb4  */
    /* JADX WARN: Code duplicated, block: B:74:0x0bbc A[DONT_INVERT] */
    /* JADX WARN: Code duplicated, block: B:75:0x0bbe  */
    /* JADX WARN: Code duplicated, block: B:77:0x0bc1  */
    /* JADX WARN: Code duplicated, block: B:78:0x0bc7  */
    /* JADX WARN: Code duplicated, block: B:79:0x0bcf  */
    /* JADX WARN: Code duplicated, block: B:80:0x0bd7  */
    /* JADX WARN: Type inference failed for: r0v1, types: [com.sec.facatfunction.aporiented.athandler.AtFailhist$1] */
    /* JADX WARN: Type inference failed for: r11v1, types: [com.sec.facatfunction.aporiented.athandler.AtBaromete$1] */
    /* JADX WARN: Type inference failed for: r7v232, types: [com.sec.facatfunction.aporiented.athandler.AtUartswit$1] */
    /* JADX WARN: Type inference failed for: r7v50, types: [com.sec.facatfunction.aporiented.athandler.AtFunctest$1] */
    /* JADX WARN: Type inference failed for: r9v61, types: [com.sec.facatfunction.aporiented.athandler.AtLightest$1] */
    /* JADX WARN: Type inference failed for: r9v7, types: [com.sec.facatfunction.aporiented.athandler.AtChipIdtt$1] */
    public final void registerAllHandler(Context context, ResponseWriter responseWriter) {
        boolean zHasSystemFeature;
        File[] fileArrListFiles;
        String str;
        RegisterCommonHandler$FPVendorChip registerCommonHandler$FPVendorChipValueOf;
        int iOrdinal;
        ResponseWriter responseWriter2;
        int i;
        FtUtil.log_d("AtParser", "registerAllHandler", "Register AT command handler");
        this.mContext = context;
        HashMap map = this.atHandlers;
        RegisterFactoryBinHandler registerFactoryBinHandler = new RegisterFactoryBinHandler();
        registerFactoryBinHandler.mContext = context;
        registerFactoryBinHandler.mAtHandlers = map;
        registerFactoryBinHandler.mWriter = responseWriter;
        FtUtil.log_d("RegisterCommonHandler", "registerCommonHandler()", "Register AT command handler for COMMON");
        map.put("AT+ACSENSOR", new AtAcsensor(context));
        map.put("AT+ACTTDATA", new AtActtdata(context));
        map.put("AT+AIRPMODE", new AtAirpmode(context));
        map.put("AT+ALERTDIS", new AtAlertdis(context, responseWriter));
        map.put("AT+APCHIPTT", new AtApchiptt(context));
        AtArpcheck atArpcheck = new AtArpcheck(context);
        atArpcheck.CMD_NAME = "ARPCHECK";
        atArpcheck.CLASS_NAME = "AtArpcheck";
        atArpcheck.NUM_ARGS = 3;
        map.put("AT+ARPCHECK", atArpcheck);
        map.put("AT+AUTHEKEY", new AtAutheKey(context));
        final AtBaromete atBaromete = new AtBaromete(context);
        atBaromete.mPressureValue = new float[5];
        atBaromete.mCurrentIndex = 0;
        atBaromete.mSenserID = new int[]{ModuleSensor.ID_MANAGER_BAROMETER, ModuleSensor.ID_FILE____BAROMETER_EEPROM};
        atBaromete.mCommonData = "";
        atBaromete.mWaitFlag = false;
        atBaromete.calcBaroDataThread = new Runnable() { // from class: com.sec.facatfunction.aporiented.athandler.AtBaromete.1
            public AnonymousClass1() {
            }

            @Override // java.lang.Runnable
            public final void run() {
                int i2 = 1;
                while (true) {
                    int i3 = i2 + 1;
                    if (i2 > 5) {
                        break;
                    }
                    String[] data = ModuleSensor.instance(AtBaromete.this.context).getData(ModuleSensor.ID_MANAGER_BAROMETER);
                    if (data != null) {
                        AtBaromete atBaromete2 = AtBaromete.this;
                        atBaromete2.mPressureValue[atBaromete2.mCurrentIndex] = Float.valueOf(data[2]).floatValue();
                        String str2 = AtBaromete.this.CLASS_NAME;
                        String str3 = "getDataBaro : " + AtBaromete.this.mCurrentIndex;
                        StringBuilder sb = new StringBuilder("mPressureValue:");
                        AtBaromete atBaromete3 = AtBaromete.this;
                        sb.append(atBaromete3.mPressureValue[atBaromete3.mCurrentIndex]);
                        FtUtil.log_i(str2, str3, sb.toString());
                        AtBaromete.this.mCurrentIndex++;
                    }
                    try {
                        Thread.sleep(100L);
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                    i2 = i3;
                }
                FtUtil.log_d(AtBaromete.this.CLASS_NAME, "calcBaroDataThread.run", "");
                int length = AtBaromete.this.mPressureValue.length;
                float f = 0.0f;
                for (int i4 = 0; i4 < length; i4++) {
                    f += AtBaromete.this.mPressureValue[i4];
                }
                String strReplace = new DecimalFormat("#.000").format(f / length).replace(",", ".");
                AtBaromete atBaromete4 = AtBaromete.this;
                atBaromete4.mCommonData = strReplace;
                AtApchiptt$$ExternalSyntheticOutline0.m("result :", strReplace, atBaromete4.CLASS_NAME, "getPressureResultUpdate");
                AtBaromete atBaromete5 = AtBaromete.this;
                if (!atBaromete5.mWaitFlag) {
                    atBaromete5.writer.write(atBaromete5.responseString("1", strReplace));
                }
                AtBaromete.this.mCurrentIndex = 0;
            }
        };
        atBaromete.CMD_NAME = "BAROMETE";
        atBaromete.CLASS_NAME = "AtBaromete";
        atBaromete.NUM_ARGS = 3;
        if (new File(Support$Path.getFilePath("BAROMETE_DELTA")).exists()) {
            FtUtil.log_d(atBaromete.CLASS_NAME, "AtBaromete", "BAROMETE_DELTAis already existed...");
        } else {
            ModuleCommon.instance(context).writemBaroDelta("0");
            Support$Path.setPermission(Support$Path.getFilePath("BAROMETE_DELTA"), true);
            FtUtil.log_d(atBaromete.CLASS_NAME, "AtBaromete", "BAROMETE_DELTA is created...");
        }
        atBaromete.writer = responseWriter;
        map.put("AT+BAROMETE", atBaromete);
        map.put("AT+BATTTEST", new AtBatttest(context, responseWriter));
        AtBootmode atBootmode = new AtBootmode(context);
        atBootmode.CMD_NAME = "BOOTMODE";
        atBootmode.CLASS_NAME = "AtBootmode";
        atBootmode.NUM_ARGS = 2;
        map.put("AT+BOOTMODE", atBootmode);
        AtBtidtest atBtidtest = new AtBtidtest(context);
        atBtidtest.subString = null;
        atBtidtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtBtidtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                String stringExtra = intent.getStringExtra("S_DATA");
                AtBtidtest atBtidtest2 = AtBtidtest.this;
                atBtidtest2.stopReceiver(atBtidtest2.mReceiver);
                if (stringExtra.equals("OK")) {
                    AtBtidtest atBtidtest3 = AtBtidtest.this;
                    FtUtil.log_d(atBtidtest3.CLASS_NAME, "mReceiver.onReceive", FtUtil.setMspSeqMessage(3, atBtidtest3.CMD_NAME.concat("=2,BTID"), "Pass"));
                    FtUtil.Sleep.sleep(50L);
                    if ("boot".equals(AtBtidtest.this.subString)) {
                        FtUtil.log_i(AtBtidtest.this.CLASS_NAME, "mReceiver.onReceive", "BT Read Boot Setting");
                        return;
                    } else {
                        AtBtidtest atBtidtest4 = AtBtidtest.this;
                        atBtidtest4.writer.write(atBtidtest4.responseString(atBtidtest4.subString, stringExtra));
                        return;
                    }
                }
                if (stringExtra.equals("NG")) {
                    AtBtidtest atBtidtest5 = AtBtidtest.this;
                    FtUtil.log_d(atBtidtest5.CLASS_NAME, "mReceiver.onReceive", FtUtil.setMspSeqMessage(3, atBtidtest5.CMD_NAME.concat("=1,0/2,BTID"), "Fail - response of BT is NG"));
                    if ("boot".equals(AtBtidtest.this.subString)) {
                        FtUtil.log_i(AtBtidtest.this.CLASS_NAME, "mReceiver.onReceive", "BT Write Boot Setting");
                        return;
                    } else {
                        AtBtidtest atBtidtest6 = AtBtidtest.this;
                        atBtidtest6.writer.write(atBtidtest6.responseString(atBtidtest6.subString, stringExtra));
                        return;
                    }
                }
                StringBuilder sb = new StringBuilder();
                FtUtil.log_i(AtBtidtest.this.CLASS_NAME, "mReceiver.onReceive", "resData: ".concat(stringExtra));
                for (String str2 : stringExtra.split(":")) {
                    sb.append(str2);
                }
                AtBtidtest atBtidtest7 = AtBtidtest.this;
                FtUtil.log_d(atBtidtest7.CLASS_NAME, "mReceiver.onReceive", FtUtil.setMspSeqMessage(3, atBtidtest7.CMD_NAME.concat("=1,0"), "Pass"));
                AtBtidtest atBtidtest8 = AtBtidtest.this;
                atBtidtest8.writer.write(atBtidtest8.responseString(atBtidtest8.subString, sb.toString()));
            }
        };
        atBtidtest.CMD_NAME = "BTIDTEST";
        atBtidtest.CLASS_NAME = "AtBtidtest";
        atBtidtest.NUM_ARGS = 2;
        atBtidtest.writer = responseWriter;
        atBtidtest.subString = "boot";
        map.put("AT+BTIDTEST", atBtidtest);
        AtBtletest atBtletest = new AtBtletest(context);
        atBtletest.first_argu = null;
        atBtletest.CMD_NAME = "BTLETEST";
        atBtletest.CLASS_NAME = "AtBtletest";
        atBtletest.NUM_ARGS = 4;
        atBtletest.writer = responseWriter;
        map.put("AT+BTLETEST", atBtletest);
        final AtChipIdtt atChipIdtt = new AtChipIdtt(context);
        atChipIdtt.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtChipIdtt.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                AtChipIdtt atChipIdtt2 = AtChipIdtt.this;
                atChipIdtt2.stopReceiver(atChipIdtt2.mReceiver);
                String action = intent.getAction();
                LiveData$$ExternalSyntheticOutline0.m("mAction : ", action, AtChipIdtt.this.CLASS_NAME, "onReceive");
                if ("com.sec.factory.camera.ACTION_TEST_STATUS".equals(action)) {
                    FtUtil.log_d(AtChipIdtt.this.CLASS_NAME, "onReceive", "ACTION_TEST_STATUS");
                    String stringExtra = intent.getStringExtra("result");
                    LiveData$$ExternalSyntheticOutline0.m("actionResult : ", stringExtra, AtChipIdtt.this.CLASS_NAME, "onReceive");
                    AtChipIdtt atChipIdtt3 = AtChipIdtt.this;
                    atChipIdtt3.writer.write(atChipIdtt3.responseString(AtChipIdtt.returnArgu, stringExtra));
                }
            }
        };
        atChipIdtt.CMD_NAME = "CHIPIDTT";
        atChipIdtt.CLASS_NAME = "AtChipIdtt";
        atChipIdtt.NUM_ARGS = 4;
        atChipIdtt.writer = responseWriter;
        map.put("AT+CHIPIDTT", atChipIdtt);
        AtCofpdata atCofpdata = new AtCofpdata(context);
        atCofpdata.CMD_NAME = "COFPDATA";
        atCofpdata.CLASS_NAME = "AtCofpdata";
        atCofpdata.NUM_ARGS = 4;
        map.put("AT+COFPDATA", atCofpdata);
        map.put("AT+CONNTEST", new AtConntest(context));
        AtControlN atControlN = new AtControlN(context);
        atControlN.CMD_NAME = "CONTROLN";
        atControlN.CLASS_NAME = "AtControlN";
        atControlN.NUM_ARGS = 2;
        String filePath = Support$Path.getFilePath("CONTROL_NO");
        if (!Support$Path.isExistFilePath(filePath)) {
            ModuleDevice.instance(context).getClass();
            Support$Path.writeNsync("CONTROL_NO", "0000000000000");
            Support$Path.setPermission(filePath, true);
        }
        map.put("AT+CONTROLN", atControlN);
        AtCountrst atCountrst = new AtCountrst(context);
        atCountrst.CMD_NAME = "COUNTRST";
        atCountrst.CLASS_NAME = "AtCountrst";
        atCountrst.NUM_ARGS = 3;
        map.put("AT+COUNTRST", atCountrst);
        map.put("AT+DEBUGLVC", new AtDebugLvC(context));
        map.put("AT+DISPTEST", new AtDisptest(context, responseWriter));
        AtEmemtest atEmemtest = new AtEmemtest(context);
        atEmemtest.CMD_NAME = "EMEMTEST";
        atEmemtest.CLASS_NAME = "AtEmemtest";
        atEmemtest.NUM_ARGS = 2;
        map.put("AT+EMEMTEST", atEmemtest);
        map.put("AT+EWRITECK", new AtEwriteck(context, responseWriter));
        AtFacmtest atFacmtest = new AtFacmtest(context);
        atFacmtest.tagId = null;
        atFacmtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFacmtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                AtFacmtest atFacmtest2 = AtFacmtest.this;
                atFacmtest2.stopReceiver(atFacmtest2.mReceiver);
                String action = intent.getAction();
                String stringExtra = intent.getStringExtra("result");
                FtUtil.log_d(AtFacmtest.this.CLASS_NAME, "onReceive", AtParser$$ExternalSyntheticOutline0.m("mAction: ", action, " extra: ", stringExtra));
                if ("com.sec.android.facm.FACMTEST_RESULT".equals(action)) {
                    FtUtil.log_d(AtFacmtest.this.CLASS_NAME, "onReceive", "FACMTEST_RESULT");
                    AtFacmtest.this.writer.write(stringExtra);
                }
            }
        };
        atFacmtest.CMD_NAME = "FACMTEST";
        atFacmtest.CLASS_NAME = "AtFacmtest";
        atFacmtest.NUM_ARGS = 4;
        atFacmtest.writer = responseWriter;
        map.put("AT+FACMTEST", atFacmtest);
        map.put("AT+FACTOLOG", new AtFactolog(context));
        AtFactorst atFactorst = new AtFactorst(context);
        atFactorst.CMD_NAME = "FACTORST";
        atFactorst.CLASS_NAME = "AtFactorst";
        atFactorst.NUM_ARGS = 2;
        map.put("AT+FACTORST", atFactorst);
        map.put("AT+FAILDUMP", new AtFaildump(context, responseWriter));
        final AtFailhist atFailhist = new AtFailhist(context);
        atFailhist.mVersion = "";
        atFailhist.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFailhist.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context2, Intent intent) {
                String action = intent.getAction();
                FtUtil.log_d(AtFailhist.this.CLASS_NAME, "onReceive", action);
                if ("com.sti.labo.AB_COUNT_RESPONSE".equals(action)) {
                    if (Support$Path.isExistFile("ABC_SUMMARY_PATH")) {
                        StringBuilder sb = new StringBuilder("OK,");
                        try {
                            InputStream inputStreamNewInputStream = Files.newInputStream(Paths.get(Support$Path.getFilePath("ABC_SUMMARY_PATH"), new String[0]), new OpenOption[0]);
                            try {
                                InputStreamReader inputStreamReader = new InputStreamReader(inputStreamNewInputStream, StandardCharsets.UTF_8);
                                try {
                                    BufferedReader bufferedReader = new BufferedReader(inputStreamReader);
                                    while (true) {
                                        try {
                                            String line = bufferedReader.readLine();
                                            if (line == null) {
                                                break;
                                            }
                                            sb.append(line.replaceAll(",", ";"));
                                            sb.append(",");
                                        } catch (Throwable th) {
                                            try {
                                                bufferedReader.close();
                                            } catch (Throwable th2) {
                                                th.addSuppressed(th2);
                                            }
                                            throw th;
                                        }
                                        try {
                                            inputStreamReader.close();
                                        } catch (Throwable th3) {
                                            th.addSuppressed(th3);
                                        }
                                        throw th;
                                    }
                                    sb.deleteCharAt(sb.length() - 1);
                                    AtFailhist atFailhist2 = AtFailhist.this;
                                    atFailhist2.writer.write(atFailhist2.responseString(atFailhist2.lastArgu, sb.toString()));
                                    bufferedReader.close();
                                    inputStreamReader.close();
                                    if (inputStreamNewInputStream != null) {
                                        inputStreamNewInputStream.close();
                                    }
                                } catch (Throwable th4) {
                                    inputStreamReader.close();
                                    throw th4;
                                }
                            } catch (Throwable th5) {
                                if (inputStreamNewInputStream != null) {
                                    try {
                                        inputStreamNewInputStream.close();
                                    } catch (Throwable th6) {
                                        th5.addSuppressed(th6);
                                    }
                                }
                                throw th5;
                            }
                        } catch (IOException e) {
                            FtUtil.log_e(e);
                        }
                    } else {
                        FtUtil.log_i(AtFailhist.this.CLASS_NAME, "handleCommand", "ABC summary file does not exist");
                        AtFailhist atFailhist3 = AtFailhist.this;
                        atFailhist3.writer.write(atFailhist3.responseString(atFailhist3.lastArgu, "NG,NO FILE"));
                    }
                }
                AtFailhist atFailhist4 = AtFailhist.this;
                atFailhist4.stopReceiver(atFailhist4.mReceiver);
            }
        };
        atFailhist.CMD_NAME = "FAILHIST";
        atFailhist.CLASS_NAME = "AtFailhist";
        atFailhist.NUM_ARGS = 3;
        atFailhist.writer = responseWriter;
        map.put("AT+FAILHIST", atFailhist);
        AtFcbttest atFcbttest = new AtFcbttest(registerFactoryBinHandler.mContext);
        atFcbttest.first_argu = null;
        atFcbttest.CMD_NAME = "FCBTTEST";
        atFcbttest.CLASS_NAME = "AtFcbttest";
        atFcbttest.NUM_ARGS = 3;
        atFcbttest.writer = responseWriter;
        map.put("AT+FCBTTEST", atFcbttest);
        HashMap map2 = registerFactoryBinHandler.mAtHandlers;
        AtFceptest atFceptest = new AtFceptest(registerFactoryBinHandler.mContext);
        atFceptest.CMD_NAME = "FCEPTEST";
        atFceptest.CLASS_NAME = "AtFceptest";
        atFceptest.NUM_ARGS = 4;
        map2.put("AT+FCEPTEST", atFceptest);
        HashMap map3 = registerFactoryBinHandler.mAtHandlers;
        Context context2 = registerFactoryBinHandler.mContext;
        AtFirmvers atFirmvers = new AtFirmvers(context2);
        atFirmvers.mTSP2UpdateStatus = "NG";
        atFirmvers.mWacomUpdateStatus = "NG";
        atFirmvers.CMD_NAME = "FIRMVERS";
        atFirmvers.CLASS_NAME = "AtFirmvers";
        atFirmvers.NUM_ARGS = 3;
        atFirmvers.mInputDeviceManager = (SemInputDeviceManager) context2.getSystemService(ContextReflection.getField("SEM_INPUT_DEVICE_SERVICE"));
        if (FactoryTest.isFactoryBinary() && Looper.myLooper() == null) {
            Looper.prepare();
        }
        map3.put("AT+FIRMVERS", atFirmvers);
        HashMap map4 = registerFactoryBinHandler.mAtHandlers;
        AtFeliCaRfCal atFeliCaRfCal = new AtFeliCaRfCal(registerFactoryBinHandler.mContext);
        atFeliCaRfCal.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFeliCaRfCal.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context3, Intent intent) {
                String action = intent.getAction();
                AtFeliCaRfCal atFeliCaRfCal2 = AtFeliCaRfCal.this;
                atFeliCaRfCal2.stopReceiver(atFeliCaRfCal2.mReceiver);
                FtUtil.Sleep.sleep(50L);
                if ("com.sec.android.app.felicatest.FELICA_TEST_RESPONSE".equals(action) || "com.sec.android.app.felicatest.FELICA_SET_EDC_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_TEST_RESPONSE");
                    String stringExtra = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal3 = AtFeliCaRfCal.this;
                    atFeliCaRfCal3.writer.write(atFeliCaRfCal3.responseString("1", stringExtra));
                    return;
                }
                if ("com.sec.android.app.felicatest.FELICA_TEST_SETNV_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_TEST_SETNV_RESPONSE");
                    String stringExtra2 = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal4 = AtFeliCaRfCal.this;
                    atFeliCaRfCal4.writer.write(atFeliCaRfCal4.responseString("0", stringExtra2));
                    return;
                }
                if ("com.sec.android.app.felicatest.FELICA_TEST_GETNV_RESPONSE".equals(action) || "com.sec.android.app.felicatest.FELICA_START_APC_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_TEST_GETNV_RESPONSE");
                    String stringExtra3 = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal5 = AtFeliCaRfCal.this;
                    atFeliCaRfCal5.writer.write(atFeliCaRfCal5.responseString("0", stringExtra3));
                    return;
                }
                if ("com.sec.android.app.felicatest.FELICA_TEST_PASS_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_TEST_PASS_RESPONSE");
                    String stringExtra4 = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal6 = AtFeliCaRfCal.this;
                    atFeliCaRfCal6.writer.write(atFeliCaRfCal6.responseString("2", stringExtra4));
                    return;
                }
                if ("com.sec.android.app.felicatest.FELICA_TEST_FAIL_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_TEST_FAIL_RESPONSE");
                    String stringExtra5 = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal7 = AtFeliCaRfCal.this;
                    atFeliCaRfCal7.writer.write(atFeliCaRfCal7.responseString("2", stringExtra5));
                    return;
                }
                if ("com.sec.android.app.felicatest.FELICA_GET_IDM_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.sec.android.app.felicatest.FELICA_GET_IDM_RESPONSE");
                    String stringExtra6 = intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal8 = AtFeliCaRfCal.this;
                    atFeliCaRfCal8.writer.write(atFeliCaRfCal8.responseString("3", stringExtra6));
                    return;
                }
                if ("com.samsung.felicalock.FELICA_LOCK_STATUS_LOCK_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.samsung.felicalock.FELICA_LOCK_STATUS_LOCK_RESPONSE");
                    intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal9 = AtFeliCaRfCal.this;
                    atFeliCaRfCal9.writer.write(atFeliCaRfCal9.responseString("4", "LOCK"));
                    return;
                }
                if ("com.samsung.felicalock.FELICA_LOCK_STATUS_UNLOCK_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.samsung.felicalock.FELICA_LOCK_STATUS_UNLOCK_RESPONSE");
                    intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal10 = AtFeliCaRfCal.this;
                    atFeliCaRfCal10.writer.write(atFeliCaRfCal10.responseString("4", "UNLOCK"));
                    return;
                }
                if ("com.samsung.felicalock.FELICA_LOCK_STATUS_ERROR_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.samsung.felicalock.FELICA_LOCK_STATUS_ERROR_RESPONSE");
                    intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal11 = AtFeliCaRfCal.this;
                    atFeliCaRfCal11.writer.write(atFeliCaRfCal11.responseString("4", "ERROR"));
                    return;
                }
                if ("com.samsung.felicalock.FELICA_LOCK_RESET_PASS_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.samsung.felicalock.FELICA_LOCK_RESET_PASS_RESPONSE");
                    intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal12 = AtFeliCaRfCal.this;
                    atFeliCaRfCal12.writer.write(atFeliCaRfCal12.responseString("4", "OK"));
                    return;
                }
                if ("com.samsung.felicalock.FELICA_LOCK_RESET_FAIL_RESPONSE".equals(action)) {
                    Log.d(AtFeliCaRfCal.this.CLASS_NAME, "com.samsung.felicalock.FELICA_LOCK_RESET_FAIL_RESPONSE");
                    intent.getStringExtra("S_DATA");
                    AtFeliCaRfCal atFeliCaRfCal13 = AtFeliCaRfCal.this;
                    atFeliCaRfCal13.writer.write(atFeliCaRfCal13.responseString("4", "NG"));
                }
            }
        };
        atFeliCaRfCal.CMD_NAME = "FLCRFCAL";
        atFeliCaRfCal.CLASS_NAME = "AtFeliCaRfCal";
        atFeliCaRfCal.NUM_ARGS = 2;
        atFeliCaRfCal.writer = responseWriter;
        map4.put("AT+FLCRFCAL", atFeliCaRfCal);
        HashMap map5 = registerFactoryBinHandler.mAtHandlers;
        AtFuelgaic atFuelgaic = new AtFuelgaic(registerFactoryBinHandler.mContext);
        atFuelgaic.CMD_NAME = "FUELGAIC";
        atFuelgaic.CLASS_NAME = "AtFuelgaic";
        atFuelgaic.NUM_ARGS = 2;
        map5.put("AT+FUELGAIC", atFuelgaic);
        HashMap map6 = registerFactoryBinHandler.mAtHandlers;
        final AtFunctest atFunctest = new AtFunctest(registerFactoryBinHandler.mContext);
        atFunctest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFunctest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context3, Intent intent) {
                String action = intent.getAction();
                if ("com.sec.factory.ACTION_AT_FUNCTEST_SEMI_TEST_RESULT".equals(action)) {
                    String stringExtra = intent.getStringExtra("response");
                    LiveData$$ExternalSyntheticOutline0.m("ACTION_SEMI_FUNCTION_TEST_RESULT response: ", stringExtra, AtFunctest.this.CLASS_NAME, "BroadcastReceiver.onReceive");
                    AtFunctest atFunctest2 = AtFunctest.this;
                    ResponseWriter responseWriter3 = atFunctest2.writer;
                    if (responseWriter3 != null) {
                        responseWriter3.write(atFunctest2.responseString("0", stringExtra));
                    }
                } else if ("com.sec.factory.ACTION_15_MAIN_START_RESULT".equals(action)) {
                    String stringExtra2 = intent.getStringExtra("response");
                    LiveData$$ExternalSyntheticOutline0.m("ACTION_15_MAIN_START_RESULT response: ", stringExtra2, AtFunctest.this.CLASS_NAME, "BroadcastReceiver.onReceive");
                    AtFunctest atFunctest3 = AtFunctest.this;
                    ResponseWriter responseWriter4 = atFunctest3.writer;
                    if (responseWriter4 != null) {
                        responseWriter4.write(atFunctest3.responseString("0", stringExtra2));
                    }
                } else if ("com.sec.factory.ACTION_15_TEST_NV_SORT_RESULT".equals(action)) {
                    String stringExtra3 = intent.getStringExtra("NV_DATA");
                    LiveData$$ExternalSyntheticOutline0.m("ACTION_15_TEST_NV_SORT_RESULT response: ", stringExtra3, AtFunctest.this.CLASS_NAME, "BroadcastReceiver.onReceive");
                    AtFunctest atFunctest4 = AtFunctest.this;
                    ResponseWriter responseWriter5 = atFunctest4.writer;
                    if (responseWriter5 != null) {
                        responseWriter5.write(atFunctest4.responseString("1", stringExtra3));
                    }
                } else if ("com.sec.factory.ACTION_PRETEST_START_RESULT".equals(action)) {
                    String stringExtra4 = intent.getStringExtra("response");
                    LiveData$$ExternalSyntheticOutline0.m("ACTION_PRETEST_START_RESULT response: ", stringExtra4, AtFunctest.this.CLASS_NAME, "BroadcastReceiver.onReceive");
                    AtFunctest atFunctest5 = AtFunctest.this;
                    ResponseWriter responseWriter6 = atFunctest5.writer;
                    if (responseWriter6 != null) {
                        responseWriter6.write(atFunctest5.responseString("0", stringExtra4));
                    }
                }
                AtFunctest atFunctest6 = AtFunctest.this;
                atFunctest6.stopReceiver(atFunctest6.mReceiver);
            }
        };
        atFunctest.CMD_NAME = "FUNCTEST";
        atFunctest.CLASS_NAME = "AtFunctest";
        atFunctest.NUM_ARGS = 2;
        atFunctest.writer = responseWriter;
        map6.put("AT+FUNCTEST", atFunctest);
        registerFactoryBinHandler.mAtHandlers.put("AT+GEOMAGSS", new AtGeomagss(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+GRIPSENS", new AtGripsens(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+GYROSCOP", new AtGyroscop(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+HAICTEST", new AtHaictest(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map7 = registerFactoryBinHandler.mAtHandlers;
        AtHeadinfo atHeadinfo = new AtHeadinfo(registerFactoryBinHandler.mContext);
        atHeadinfo.CMD_NAME = "HEADINFO";
        atHeadinfo.CLASS_NAME = "AtHeadinfo";
        atHeadinfo.NUM_ARGS = 2;
        map7.put("AT+HEADINFO", atHeadinfo);
        HashMap map8 = registerFactoryBinHandler.mAtHandlers;
        AtHmacmism atHmacmism = new AtHmacmism(registerFactoryBinHandler.mContext);
        atHmacmism.CMD_NAME = "HMACMISM";
        atHmacmism.CLASS_NAME = "AtHmacmism";
        atHmacmism.NUM_ARGS = 3;
        map8.put("AT+HMACMISM", atHmacmism);
        HashMap map9 = registerFactoryBinHandler.mAtHandlers;
        Context context3 = registerFactoryBinHandler.mContext;
        AtHrmosens atHrmosens = new AtHrmosens(context3);
        atHrmosens.mSensorID = null;
        atHrmosens.updatedState = false;
        atHrmosens.res = null;
        atHrmosens.mModuleSensor = null;
        atHrmosens.CMD_NAME = "HRMOSENS";
        atHrmosens.CLASS_NAME = "AtHrmosens";
        atHrmosens.NUM_ARGS = 3;
        atHrmosens.mModuleSensor = ModuleSensor.instance(context3);
        ((DecimalFormat) NumberFormat.getInstance(Locale.ENGLISH)).applyPattern("0.00");
        atHrmosens.writer = responseWriter;
        map9.put("AT+HRMOSENS", atHrmosens);
        HashMap map10 = registerFactoryBinHandler.mAtHandlers;
        AtHwindick atHwindick = new AtHwindick(registerFactoryBinHandler.mContext);
        atHwindick.CMD_NAME = "HWINDICK";
        atHwindick.CLASS_NAME = "AtHwindick";
        atHwindick.NUM_ARGS = 2;
        map10.put("AT+HWINDICK", atHwindick);
        registerFactoryBinHandler.mAtHandlers.put("AT+HWPARAMD", new AtHwparamd(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map11 = registerFactoryBinHandler.mAtHandlers;
        Context context4 = registerFactoryBinHandler.mContext;
        AtIdChiptt atIdChiptt = new AtIdChiptt(context4);
        atIdChiptt.CMD_NAME = "IDCHIPTT";
        atIdChiptt.CLASS_NAME = "AtIdChiptt";
        atIdChiptt.NUM_ARGS = 3;
        if (context4.getPackageManager().hasSystemFeature("android.hardware.nfc")) {
            try {
                atIdChiptt.mSamsungNfcAdapter = SamsungNfcAdapter.getDefaultAdapter(context4.getApplicationContext());
            } catch (NoClassDefFoundError unused) {
                FtUtil.log_d(atIdChiptt.CLASS_NAME, "getSamsungNfcAdapterInstance", "SamsungNfcAdapter is null due to be NoClassDefFoundError");
            }
        }
        atIdChiptt.writer = responseWriter;
        map11.put("AT+IDCHIPTT", atIdChiptt);
        registerFactoryBinHandler.mAtHandlers.put("AT+IFPMICCN", new AtIfpmiccn(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map12 = registerFactoryBinHandler.mAtHandlers;
        AtImemtest atImemtest = new AtImemtest(registerFactoryBinHandler.mContext);
        atImemtest.CMD_NAME = "IMEMTEST";
        atImemtest.CLASS_NAME = "AtImemtest";
        atImemtest.NUM_ARGS = 2;
        map12.put("AT+IMEMTEST", atImemtest);
        HashMap map13 = registerFactoryBinHandler.mAtHandlers;
        AtKey atKey = new AtKey(registerFactoryBinHandler.mContext);
        atKey.CMD_NAME = "KEY";
        atKey.CLASS_NAME = "AtKey";
        atKey.NUM_ARGS = 1;
        map13.put("AT+KEY", atKey);
        HashMap map14 = registerFactoryBinHandler.mAtHandlers;
        AtKeyhold atKeyhold = new AtKeyhold(registerFactoryBinHandler.mContext);
        atKeyhold.CMD_NAME = "KEYHOLD";
        atKeyhold.CLASS_NAME = "AtKeyHold";
        atKeyhold.NUM_ARGS = 1;
        map14.put("AT+KEYHOLD", atKeyhold);
        HashMap map15 = registerFactoryBinHandler.mAtHandlers;
        AtKstringb atKstringb = new AtKstringb(registerFactoryBinHandler.mContext);
        atKstringb.CMD_NAME = "KSTRINGB";
        atKstringb.CLASS_NAME = "AtKstringb";
        atKstringb.NUM_ARGS = 2;
        map15.put("AT+KSTRINGB", atKstringb);
        HashMap map16 = registerFactoryBinHandler.mAtHandlers;
        Context context5 = registerFactoryBinHandler.mContext;
        AtLanguset atLanguset = new AtLanguset(context5);
        atLanguset.CMD_NAME = "LANGUSET";
        atLanguset.CLASS_NAME = "AtLanguset";
        atLanguset.NUM_ARGS = 2;
        atLanguset.mContext = context5;
        map16.put("AT+LANGUSET", atLanguset);
        registerFactoryBinHandler.mAtHandlers.put("AT+LDUCCSUM", new AtLduccsum(registerFactoryBinHandler.mContext));
        HashMap map17 = registerFactoryBinHandler.mAtHandlers;
        AtLedlampt atLedlampt = new AtLedlampt(registerFactoryBinHandler.mContext);
        atLedlampt.CMD_NAME = "LEDLAMPT";
        atLedlampt.CLASS_NAME = "AtLedlampt";
        atLedlampt.NUM_ARGS = 2;
        map17.put("AT+LEDLAMPT", atLedlampt);
        HashMap map18 = registerFactoryBinHandler.mAtHandlers;
        Context context6 = registerFactoryBinHandler.mContext;
        final AtLightest atLightest = new AtLightest(context6);
        atLightest.mSensorID = null;
        atLightest.mSensorID_LIGHT_LUX = -1;
        atLightest.mSensorID_LIGHT_CCT = -1;
        atLightest.mSensorID_LIGHT_RGB = -1;
        new IntentFilter();
        atLightest.lock = new Object();
        atLightest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtLightest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context7, Intent intent) {
                synchronized (AtLightest.this) {
                    AtLightest atLightest2 = AtLightest.this;
                    atLightest2.stopReceiver(atLightest2.mReceiver);
                }
                String action = intent.getAction();
                LiveData$$ExternalSyntheticOutline0.m("action : ", action, AtLightest.this.CLASS_NAME, "onReceive");
                if ("com.sec.factory.LIGHT_CAL_RESPONSE".equals(action) || "com.sec.factory.LIGHT_HIGH_LOW_RESPONSE".equals(action)) {
                    String stringExtra = intent.getStringExtra("completed");
                    String stringExtra2 = intent.getStringExtra("result");
                    LiveData$$ExternalSyntheticOutline0.m("extra_completed : ", stringExtra, AtLightest.this.CLASS_NAME, "onReceive");
                    synchronized (AtLightest.this.lock) {
                        try {
                            if ("OK".equalsIgnoreCase(stringExtra)) {
                                FtUtil.log_d(AtLightest.this.CLASS_NAME, "onReceive", "extra_result : " + stringExtra2);
                                AtLightest atLightest3 = AtLightest.this;
                                atLightest3.writer.write(atLightest3.responseString(atLightest3.returnArgu, stringExtra2));
                            } else {
                                AtLightest atLightest4 = AtLightest.this;
                                atLightest4.writer.write(atLightest4.responseNG(atLightest4.returnArgu));
                            }
                        } catch (Throwable th) {
                            throw th;
                        }
                    }
                }
            }
        };
        atLightest.CMD_NAME = "LIGHTEST";
        atLightest.CLASS_NAME = "AtLightest";
        atLightest.NUM_ARGS = 2;
        atLightest.writer = responseWriter;
        atLightest.mModulePower = ModulePower.instance(context6);
        atLightest.mModuleSensor = ModuleSensor.instance(context6);
        map18.put("AT+LIGHTEST", atLightest);
        HashMap map19 = registerFactoryBinHandler.mAtHandlers;
        AtLineinfo atLineinfo = new AtLineinfo(registerFactoryBinHandler.mContext);
        atLineinfo.CMD_NAME = "LINEINFO";
        atLineinfo.CLASS_NAME = "AtLineinfo";
        atLineinfo.NUM_ARGS = 3;
        map19.put("AT+LINEINFO", atLineinfo);
        registerFactoryBinHandler.mAtHandlers.put("AT+LOOPTEST", new AtLooptest(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+NCAMTEST", new AtNcamtest(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map20 = registerFactoryBinHandler.mAtHandlers;
        AtGcamtest atGcamtest = new AtGcamtest(registerFactoryBinHandler.mContext);
        atGcamtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtGcamtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context7, Intent intent) {
                AtGcamtest atGcamtest2 = AtGcamtest.this;
                atGcamtest2.stopReceiver(atGcamtest2.mReceiver);
                String action = intent.getAction();
                LiveData$$ExternalSyntheticOutline0.m("mAction : ", action, AtGcamtest.this.CLASS_NAME, "onReceive");
                if ("com.sec.factory.gccamera.ACTION_TEST_STATUS".equals(action)) {
                    String stringExtra = intent.getStringExtra("result");
                    LiveData$$ExternalSyntheticOutline0.m("mActionResult : ", stringExtra, AtGcamtest.this.CLASS_NAME, "onReceive");
                    AtGcamtest atGcamtest3 = AtGcamtest.this;
                    atGcamtest3.writer.write(atGcamtest3.responseString(AtGcamtest.returnArgu, stringExtra));
                }
            }
        };
        atGcamtest.CMD_NAME = "GCAMTEST";
        atGcamtest.CLASS_NAME = "AtGcamtest";
        atGcamtest.NUM_ARGS = 3;
        atGcamtest.writer = responseWriter;
        map20.put("AT+GCAMTEST", atGcamtest);
        HashMap map21 = registerFactoryBinHandler.mAtHandlers;
        AtNeedcmdt atNeedcmdt = new AtNeedcmdt(registerFactoryBinHandler.mContext);
        atNeedcmdt.CMD_NAME = "NEEDCMDT";
        atNeedcmdt.CLASS_NAME = "AtNeedcmdt";
        atNeedcmdt.NUM_ARGS = 4;
        map21.put("AT+NEEDCMDT", atNeedcmdt);
        registerFactoryBinHandler.mAtHandlers.put("AT+NFCMTEST", new AtNfcmtest(registerFactoryBinHandler.mContext, responseWriter));
        registerFactoryBinHandler.mAtHandlers.put("AT+OQCSBFTT", new AtOqcsbftt(registerFactoryBinHandler.mContext));
        HashMap map22 = registerFactoryBinHandler.mAtHandlers;
        AtPdpbacku atPdpbacku = new AtPdpbacku(registerFactoryBinHandler.mContext);
        atPdpbacku.CMD_NAME = "PDPBACKU";
        atPdpbacku.CLASS_NAME = "AtPdpbacku";
        atPdpbacku.NUM_ARGS = 3;
        map22.put("AT+PDPBACKU", atPdpbacku);
        HashMap map23 = registerFactoryBinHandler.mAtHandlers;
        AtPowreset atPowreset = new AtPowreset(registerFactoryBinHandler.mContext);
        atPowreset.CMD_NAME = "POWRESET";
        atPowreset.CLASS_NAME = "AtPowreset";
        atPowreset.NUM_ARGS = 2;
        map23.put("AT+POWRESET", atPowreset);
        HashMap map24 = registerFactoryBinHandler.mAtHandlers;
        AtPreconfg atPreconfg = new AtPreconfg(registerFactoryBinHandler.mContext);
        atPreconfg.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtPreconfg.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context7, Intent intent) {
                String action = intent.getAction();
                AtApchiptt$$ExternalSyntheticOutline0.m("Get intent : ", action, AtPreconfg.this.CLASS_NAME, "onReceive");
                if ("com.sec.factory.aporiented.athandler.atpreconfg".equals(action)) {
                    String stringExtra = intent.getStringExtra("code");
                    AtApchiptt$$ExternalSyntheticOutline0.m("code value : ", stringExtra, AtPreconfg.this.CLASS_NAME, "onReceive");
                    AtPreconfg atPreconfg2 = AtPreconfg.this;
                    atPreconfg2.writer.write(atPreconfg2.responseString("0", stringExtra));
                    AtPreconfg atPreconfg3 = AtPreconfg.this;
                    atPreconfg3.stopReceiver(atPreconfg3.mReceiver);
                }
            }
        };
        atPreconfg.CMD_NAME = "PRECONFG";
        atPreconfg.CLASS_NAME = "AtPreconfg";
        atPreconfg.NUM_ARGS = 2;
        atPreconfg.writer = responseWriter;
        map24.put("AT+PRECONFG", atPreconfg);
        HashMap map25 = registerFactoryBinHandler.mAtHandlers;
        Context context7 = registerFactoryBinHandler.mContext;
        AtProximit atProximit = new AtProximit(context7);
        atProximit.mSensorProximity = null;
        atProximit.isPassCheckingADC = true;
        atProximit.m_nStartTime = 0L;
        atProximit.m_nPrivADC = 0;
        atProximit.CMD_NAME = "PROXIMIT";
        atProximit.CLASS_NAME = "AtProximit";
        atProximit.NUM_ARGS = 2;
        String sensorName = SensorDeviceInfo.getSensorName(SensorDeviceInfo.TYPE_PROXIMITY, 1);
        FtUtil.log_i(atProximit.CLASS_NAME, "sensorName : " + sensorName);
        atProximit.mSensorProximity = new SensorProximity(context7);
        map25.put("AT+PROXIMIT", atProximit);
        HashMap map26 = registerFactoryBinHandler.mAtHandlers;
        AtRamsizec atRamsizec = new AtRamsizec(registerFactoryBinHandler.mContext);
        atRamsizec.CMD_NAME = "RAMSIZEC";
        atRamsizec.CLASS_NAME = "AtRamSizec";
        atRamsizec.NUM_ARGS = 3;
        map26.put("AT+RAMSIZEC", atRamsizec);
        HashMap map27 = registerFactoryBinHandler.mAtHandlers;
        AtRapplist atRapplist = new AtRapplist(registerFactoryBinHandler.mContext);
        atRapplist.CMD_NAME = "RAPPLIST";
        atRapplist.CLASS_NAME = "AtRapplist";
        atRapplist.NUM_ARGS = 4;
        map27.put("AT+RAPPLIST", atRapplist);
        registerFactoryBinHandler.mAtHandlers.put("AT+READRSSI", new AtReadRssi(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+RGBPDISP", new AtRgbpdisp(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map28 = registerFactoryBinHandler.mAtHandlers;
        AtRstcompc atRstcompc = new AtRstcompc(registerFactoryBinHandler.mContext);
        atRstcompc.CMD_NAME = "RSTCOMPC";
        atRstcompc.CLASS_NAME = "AtRstcompc";
        atRstcompc.NUM_ARGS = 3;
        map28.put("AT+RSTCOMPC", atRstcompc);
        HashMap map29 = registerFactoryBinHandler.mAtHandlers;
        AtRstcount atRstcount = new AtRstcount(registerFactoryBinHandler.mContext);
        atRstcount.CMD_NAME = "RSTCOUNT";
        atRstcount.CLASS_NAME = "AtRstcount";
        atRstcount.NUM_ARGS = 3;
        map29.put("AT+RSTCOUNT", atRstcount);
        HashMap map30 = registerFactoryBinHandler.mAtHandlers;
        AtScampara atScampara = new AtScampara(registerFactoryBinHandler.mContext);
        atScampara.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtScampara.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context8, Intent intent) {
                AtScampara atScampara2 = AtScampara.this;
                atScampara2.stopReceiver(atScampara2.mReceiver);
                String action = intent.getAction();
                FtUtil.log_d(AtScampara.this.CLASS_NAME, "onReceive", action);
                if ("com.sec.factory.camera.ACTION_TEST_STATUS".equals(action)) {
                    FtUtil.log_d(AtScampara.this.CLASS_NAME, "onReceive", "ACTION_TEST_STATUS");
                    String stringExtra = intent.getStringExtra("result");
                    String stringExtra2 = intent.getStringExtra("result_details");
                    if ("OK".equalsIgnoreCase(stringExtra)) {
                        if (stringExtra2 == null || stringExtra2.equalsIgnoreCase("")) {
                            AtScampara atScampara3 = AtScampara.this;
                            atScampara3.writer.write(atScampara3.responseOK(AtScampara.returnArgu));
                            return;
                        } else {
                            FtUtil.log_d(AtScampara.this.CLASS_NAME, "onReceive", "result_details : ".concat(stringExtra2));
                            AtScampara atScampara4 = AtScampara.this;
                            atScampara4.writer.write(atScampara4.responseString(AtScampara.returnArgu, "OK,".concat(stringExtra2)));
                            return;
                        }
                    }
                    if (stringExtra2 == null || stringExtra2.equalsIgnoreCase("")) {
                        AtScampara atScampara5 = AtScampara.this;
                        atScampara5.writer.write(atScampara5.responseString(AtScampara.returnArgu, "NG"));
                    } else {
                        FtUtil.log_d(AtScampara.this.CLASS_NAME, "onReceive", "result_details : ".concat(stringExtra2));
                        AtScampara atScampara6 = AtScampara.this;
                        atScampara6.writer.write(atScampara6.responseString(AtScampara.returnArgu, "NG,".concat(stringExtra2)));
                    }
                }
            }
        };
        atScampara.CMD_NAME = "SCAMPARA";
        atScampara.CLASS_NAME = "AtScampara";
        atScampara.NUM_ARGS = 4;
        atScampara.writer = responseWriter;
        map30.put("AT+SCAMPARA", atScampara);
        HashMap map31 = registerFactoryBinHandler.mAtHandlers;
        AtSecurebt atSecurebt = new AtSecurebt(registerFactoryBinHandler.mContext);
        atSecurebt.CMD_NAME = "SECUREBT";
        atSecurebt.CLASS_NAME = "AtSecurebt";
        atSecurebt.NUM_ARGS = 3;
        map31.put("AT+SECUREBT", atSecurebt);
        HashMap map32 = registerFactoryBinHandler.mAtHandlers;
        AtSelftest atSelftest = new AtSelftest(registerFactoryBinHandler.mContext);
        atSelftest.CMD_NAME = "SELFTEST";
        atSelftest.CLASS_NAME = "AtSelftest";
        atSelftest.NUM_ARGS = 3;
        map32.put("AT+SELFTEST", atSelftest);
        HashMap map33 = registerFactoryBinHandler.mAtHandlers;
        AtSensorHb atSensorHb = new AtSensorHb(registerFactoryBinHandler.mContext);
        atSensorHb.CMD_NAME = "SENSORHB";
        atSensorHb.CLASS_NAME = "AtSensorHb";
        atSensorHb.NUM_ARGS = 3;
        map33.put("AT+SENSORHB", atSensorHb);
        HashMap map34 = registerFactoryBinHandler.mAtHandlers;
        Context context8 = registerFactoryBinHandler.mContext;
        AtSerialno atSerialno = new AtSerialno(context8);
        atSerialno.CMD_NAME = "SERIALNO";
        atSerialno.CLASS_NAME = "AtSerialno";
        atSerialno.NUM_ARGS = 2;
        String filePath2 = Support$Path.getFilePath("SERIAL_NO");
        if (!Support$Path.isExistFilePath(filePath2)) {
            ModuleDevice.instance(context8).getClass();
            Support$Path.writeNsync("SERIAL_NO", "00000000000");
            Support$Path.setPermission(filePath2, true);
        }
        map34.put("AT+SERIALNO", atSerialno);
        HashMap map35 = registerFactoryBinHandler.mAtHandlers;
        AtSvcainit atSvcainit = new AtSvcainit(registerFactoryBinHandler.mContext);
        atSvcainit.CMD_NAME = "SVCAINIT";
        atSvcainit.CLASS_NAME = "AtSvcainit";
        atSvcainit.NUM_ARGS = 3;
        map35.put("AT+SVCAINIT", atSvcainit);
        HashMap map36 = registerFactoryBinHandler.mAtHandlers;
        AtSwdlmode atSwdlmode = new AtSwdlmode(registerFactoryBinHandler.mContext);
        atSwdlmode.CMD_NAME = "SWDLMODE";
        atSwdlmode.CLASS_NAME = "AtSwdlmode";
        atSwdlmode.NUM_ARGS = 1;
        map36.put("AT+SWDLMODE", atSwdlmode);
        HashMap map37 = registerFactoryBinHandler.mAtHandlers;
        Context context9 = registerFactoryBinHandler.mContext;
        AtSwizSkip atSwizSkip = new AtSwizSkip(context9);
        atSwizSkip.CMD_NAME = "SWIZSKIP";
        atSwizSkip.CLASS_NAME = "AtSwizSkip";
        atSwizSkip.NUM_ARGS = 2;
        atSwizSkip.contextResolver = context9.getContentResolver();
        atSwizSkip.pm = context9.getPackageManager();
        SemSystemProperties.set("sys.factory.atswizskip", "true");
        ModuleDevice moduleDeviceInstance = ModuleDevice.instance(context9);
        moduleDeviceInstance.getClass();
        try {
            zHasSystemFeature = moduleDeviceInstance.mContext.getPackageManager().hasSystemFeature("android.hardware.type.watch");
        } catch (Error | Exception unused2) {
            zHasSystemFeature = false;
        }
        atSwizSkip.watchDev = zHasSystemFeature;
        map37.put("AT+SWIZSKIP", atSwizSkip);
        HashMap map38 = registerFactoryBinHandler.mAtHandlers;
        AtSysscope atSysscope = new AtSysscope(registerFactoryBinHandler.mContext);
        atSysscope.CMD_NAME = "SYSSCOPE";
        atSysscope.CLASS_NAME = "AtSysscope";
        atSysscope.NUM_ARGS = 2;
        atSysscope.writer = responseWriter;
        atSysscope.changeSysScopeStatus();
        map38.put("AT+SYSSCOPE", atSysscope);
        HashMap map39 = registerFactoryBinHandler.mAtHandlers;
        Context context10 = registerFactoryBinHandler.mContext;
        AtSyssleep atSyssleep = new AtSyssleep(context10);
        atSyssleep.limitedPowerOffDelay = 0;
        atSyssleep.mContext = context10;
        atSyssleep.CMD_NAME = "SYSSLEEP";
        atSyssleep.CLASS_NAME = "AtSyssleep";
        atSyssleep.NUM_ARGS = 2;
        map39.put("AT+SYSSLEEP", atSyssleep);
        registerFactoryBinHandler.mAtHandlers.put("AT+TEMPTEST", new AtTemptest(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+TESTAPKU", new AtTestapku(registerFactoryBinHandler.mContext));
        HashMap map40 = registerFactoryBinHandler.mAtHandlers;
        AtTjiginfo atTjiginfo = new AtTjiginfo(registerFactoryBinHandler.mContext);
        atTjiginfo.CMD_NAME = "TJIGINFO";
        atTjiginfo.CLASS_NAME = "AtTjiginfo";
        atTjiginfo.NUM_ARGS = 3;
        atTjiginfo.writer = responseWriter;
        map40.put("AT+TJIGINFO", atTjiginfo);
        HashMap map41 = registerFactoryBinHandler.mAtHandlers;
        AtTouch atTouch = new AtTouch(registerFactoryBinHandler.mContext);
        atTouch.CMD_NAME = "TOUCH";
        atTouch.CLASS_NAME = "AtTouch";
        atTouch.NUM_ARGS = 3;
        map41.put("AT+TOUCH", atTouch);
        registerFactoryBinHandler.mAtHandlers.put("AT+TSPPTEST", new AtTspptestStandard(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map42 = registerFactoryBinHandler.mAtHandlers;
        AtTssCheck atTssCheck = new AtTssCheck(registerFactoryBinHandler.mContext);
        atTssCheck.CMD_NAME = "TSSCHECK";
        atTssCheck.CLASS_NAME = "AtTssCheck";
        atTssCheck.NUM_ARGS = 3;
        map42.put("AT+TSSCHECK", atTssCheck);
        HashMap map43 = registerFactoryBinHandler.mAtHandlers;
        final AtUartswit atUartswit = new AtUartswit(registerFactoryBinHandler.mContext);
        atUartswit.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtUartswit.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context11, Intent intent) {
                if (intent.getAction().equals("com.sec.factory.aporiented.athandler.AtUartswit.SetUartPath")) {
                    String stringExtra = intent.getStringExtra("PATH");
                    LiveData$$ExternalSyntheticOutline0.m("com.sec.factory.aporiented.athandler.AtUartswit.SetUartPath : Set : ", stringExtra, AtUartswit.this.CLASS_NAME, "onReceive");
                    AtUartswit.this.writer.write(stringExtra);
                }
            }
        };
        atUartswit.CMD_NAME = "UARTSWIT";
        atUartswit.CLASS_NAME = "AtUartswit";
        atUartswit.NUM_ARGS = 2;
        atUartswit.writer = responseWriter;
        map43.put("AT+UARTSWIT", atUartswit);
        registerFactoryBinHandler.mAtHandlers.put("AT+UBCTTEST", new AtUbcttest(registerFactoryBinHandler.mContext));
        HashMap map44 = registerFactoryBinHandler.mAtHandlers;
        AtUencrypt atUencrypt = new AtUencrypt(registerFactoryBinHandler.mContext);
        atUencrypt.CMD_NAME = "UENCRYPT";
        atUencrypt.CLASS_NAME = "AtUencrypt";
        atUencrypt.NUM_ARGS = 3;
        map44.put("AT+UENCRYPT", atUencrypt);
        HashMap map45 = registerFactoryBinHandler.mAtHandlers;
        AtUsbdebug atUsbdebug = new AtUsbdebug(registerFactoryBinHandler.mContext);
        atUsbdebug.CMD_NAME = "USBDEBUG";
        atUsbdebug.CLASS_NAME = "AtUsbdebug";
        atUsbdebug.NUM_ARGS = 1;
        map45.put("AT+USBDEBUG", atUsbdebug);
        HashMap map46 = registerFactoryBinHandler.mAtHandlers;
        AtUserdata atUserdata = new AtUserdata(registerFactoryBinHandler.mContext);
        atUserdata.CMD_NAME = "USERDATA";
        atUserdata.CLASS_NAME = "AtUserdata";
        atUserdata.NUM_ARGS = 3;
        map46.put("AT+USERDATA", atUserdata);
        HashMap map47 = registerFactoryBinHandler.mAtHandlers;
        AtUwbdtest atUwbdtest = new AtUwbdtest(registerFactoryBinHandler.mContext);
        atUwbdtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtUwbdtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context11, Intent intent) {
                if ("com.samsung.android.uwb.test.action.RESPONSE".equals(intent.getAction())) {
                    AtUwbdtest atUwbdtest2 = AtUwbdtest.this;
                    atUwbdtest2.context.unregisterReceiver(atUwbdtest2.mReceiver);
                    String stringExtra = intent.getStringExtra("com.samsung.android.uwb.test.extra.DATA_STRING");
                    if (stringExtra == null) {
                        stringExtra = intent.getStringExtra("com.samsung.android.uwb.test.extra.DATA_INTEGER");
                    }
                    int intExtra = intent.getIntExtra("com.samsung.android.uwb.test.extra.ID", 0);
                    DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra, "resCmd: ", AtUwbdtest.this.CLASS_NAME, "onReceive");
                    AtUwbdtest atUwbdtest3 = AtUwbdtest.this;
                    atUwbdtest3.writer.write(atUwbdtest3.responseString(String.format("%d", Integer.valueOf(intExtra)), stringExtra));
                }
            }
        };
        atUwbdtest.CMD_NAME = "UWBDTEST";
        atUwbdtest.CLASS_NAME = "AtUwbdtest";
        atUwbdtest.NUM_ARGS = 4;
        atUwbdtest.writer = responseWriter;
        map47.put("AT+UWBDTEST", atUwbdtest);
        registerFactoryBinHandler.mAtHandlers.put("AT+VERSNAME", new AtVersname(registerFactoryBinHandler.mContext));
        registerFactoryBinHandler.mAtHandlers.put("AT+VIBRTEST", new AtVibrtest(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map48 = registerFactoryBinHandler.mAtHandlers;
        AtWColorid atWColorid = new AtWColorid(registerFactoryBinHandler.mContext);
        atWColorid.CMD_NAME = "WCOLORID";
        atWColorid.CLASS_NAME = "AtWColorid";
        atWColorid.NUM_ARGS = 4;
        map48.put("AT+WCOLORID", atWColorid);
        registerFactoryBinHandler.mAtHandlers.put("AT+WIFIIDRW", new AtWifiidrw(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map49 = registerFactoryBinHandler.mAtHandlers;
        AtWifitest atWifitest = new AtWifitest(registerFactoryBinHandler.mContext);
        atWifitest.mWlanTest = 0;
        atWifitest.isReceivedATCommands = false;
        atWifitest.first_argu = null;
        atWifitest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtWifitest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context11, Intent intent) {
                String action = intent.getAction();
                LiveData$$ExternalSyntheticOutline0.m("Action: ", action, AtWifitest.this.CLASS_NAME, "handleCommand");
                AtWifitest atWifitest2 = AtWifitest.this;
                if (!atWifitest2.isReceivedATCommands) {
                    atWifitest2.stopReceiver(atWifitest2.mReceiver);
                    FtUtil.log_w(AtWifitest.this.CLASS_NAME, "handleCommand", "isReceivedATCommands: " + AtWifitest.this.isReceivedATCommands);
                    return;
                }
                if ("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE".equals(action)) {
                    AtWifitest atWifitest3 = AtWifitest.this;
                    atWifitest3.stopReceiver(atWifitest3.mReceiver);
                    AtWifitest atWifitest4 = AtWifitest.this;
                    atWifitest4.writer.write(atWifitest4.responseString(atWifitest4.first_argu, intent.getStringExtra("S_DATA")));
                    return;
                }
                if ("android.intent.action.WIFI_DRIVER_INDICATION".equals(action)) {
                    FtUtil.log_d(AtWifitest.this.CLASS_NAME, "handleCommand", "Status: " + intent.getStringExtra("STATUS"));
                    if (!intent.getStringExtra("STATUS").equals("ready")) {
                        AtWifitest.this.mWlanTest = 0;
                        return;
                    }
                    AtWifitest atWifitest5 = AtWifitest.this;
                    atWifitest5.mWlanTest = 1;
                    atWifitest5.handleCommand(atWifitest5.savedArgu);
                }
            }
        };
        atWifitest.CMD_NAME = "WIFITEST";
        atWifitest.CLASS_NAME = "AtWifitest";
        atWifitest.NUM_ARGS = 4;
        atWifitest.writer = responseWriter;
        map49.put("AT+WIFITEST", atWifitest);
        HashMap map50 = registerFactoryBinHandler.mAtHandlers;
        AtWprotect atWprotect = new AtWprotect(registerFactoryBinHandler.mContext);
        atWprotect.CMD_NAME = "WPROTECT";
        atWprotect.CLASS_NAME = "AtWprotect";
        atWprotect.NUM_ARGS = 2;
        map50.put("AT+WPROTECT", atWprotect);
        HashMap map51 = registerFactoryBinHandler.mAtHandlers;
        AtApMemCrc atApMemCrc = new AtApMemCrc(registerFactoryBinHandler.mContext);
        atApMemCrc.CMD_NAME = "APMEMCRC";
        atApMemCrc.CLASS_NAME = "AtApMemCrc";
        atApMemCrc.NUM_ARGS = 3;
        map51.put("AT+APMEMCRC", atApMemCrc);
        registerFactoryBinHandler.mAtHandlers.put("AT+PMICTEST", new AtPmictest(registerFactoryBinHandler.mContext));
        HashMap map52 = registerFactoryBinHandler.mAtHandlers;
        AtBrightcn atBrightcn = new AtBrightcn(registerFactoryBinHandler.mContext);
        atBrightcn.CMD_NAME = "BRIGHTCN";
        atBrightcn.CLASS_NAME = "AtBrightcn";
        atBrightcn.NUM_ARGS = 3;
        map52.put("AT+BRIGHTCN", atBrightcn);
        HashMap map53 = registerFactoryBinHandler.mAtHandlers;
        AtQuestchk atQuestchk = new AtQuestchk(registerFactoryBinHandler.mContext);
        atQuestchk.CMD_NAME = "QUESTCHK";
        atQuestchk.CLASS_NAME = "AtQuestchk";
        atQuestchk.NUM_ARGS = 2;
        map53.put("AT+QUESTCHK", atQuestchk);
        HashMap map54 = registerFactoryBinHandler.mAtHandlers;
        Context context11 = registerFactoryBinHandler.mContext;
        AtCteicode atCteicode = new AtCteicode(context11);
        atCteicode.CMD_NAME = "CTEICODE";
        atCteicode.CLASS_NAME = "AtCteicode";
        atCteicode.NUM_ARGS = 2;
        String filePath3 = Support$Path.getFilePath("SECEFS_CTEICODE");
        if (!Support$Path.isExistFilePath(filePath3)) {
            ModuleDevice.instance(context11).getClass();
            Support$Path.writeNsync("SECEFS_CTEICODE", "");
            Support$Path.setPermission(filePath3, true);
        }
        map54.put("AT+CTEICODE", atCteicode);
        HashMap map55 = registerFactoryBinHandler.mAtHandlers;
        AtSimdetec atSimdetec = new AtSimdetec(registerFactoryBinHandler.mContext);
        atSimdetec.CMD_NAME = "SIMDETEC";
        atSimdetec.CLASS_NAME = "AtSimdetec";
        map55.put("AT+SIMDETEC", atSimdetec);
        registerFactoryBinHandler.mAtHandlers.put("AT+SPECCHAN", new AtSpecchan(registerFactoryBinHandler.mContext, responseWriter));
        HashMap map56 = registerFactoryBinHandler.mAtHandlers;
        AtVsimtchk atVsimtchk = new AtVsimtchk(registerFactoryBinHandler.mContext);
        atVsimtchk.CMD_NAME = "VSIMTCHK";
        atVsimtchk.CLASS_NAME = "AtVsimtchk";
        atVsimtchk.NUM_ARGS = 3;
        map56.put("AT+VSIMTCHK", atVsimtchk);
        HashMap map57 = registerFactoryBinHandler.mAtHandlers;
        AtSqtPachk atSqtPachk = new AtSqtPachk(registerFactoryBinHandler.mContext);
        atSqtPachk.CMD_NAME = "SQTPACHK";
        atSqtPachk.CLASS_NAME = "AtSqtPachk";
        atSqtPachk.NUM_ARGS = 2;
        if (Support$Path.getProp("ro.soc.model").matches("^s5e.*")) {
            atSqtPachk.path = "/dev/block/by-name/nad_fw";
        } else {
            atSqtPachk.path = "/dev/block/by-name/catefv";
        }
        map57.put("AT+SQTPACHK", atSqtPachk);
        HashMap map58 = registerFactoryBinHandler.mAtHandlers;
        AtCtrlpApk atCtrlpApk = new AtCtrlpApk(registerFactoryBinHandler.mContext);
        atCtrlpApk.CMD_NAME = "CTRLPAPK";
        atCtrlpApk.CLASS_NAME = "AtCtrlpApk";
        atCtrlpApk.NUM_ARGS = 3;
        map58.put("AT+CTRLPAPK", atCtrlpApk);
        HashMap map59 = registerFactoryBinHandler.mAtHandlers;
        AtDatasave atDatasave = new AtDatasave(registerFactoryBinHandler.mContext);
        atDatasave.CMD_NAME = "DATADAVE";
        atDatasave.CLASS_NAME = "AtDatasave";
        atDatasave.NUM_ARGS = 4;
        map59.put("AT+DATASAVE", atDatasave);
        HashMap map60 = registerFactoryBinHandler.mAtHandlers;
        AtFcfmtest atFcfmtest = new AtFcfmtest(registerFactoryBinHandler.mContext);
        atFcfmtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFcfmtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final synchronized void onReceive(Context context12, Intent intent) {
                try {
                    String action = intent.getAction();
                    FtUtil.log_i(AtFcfmtest.this.CLASS_NAME, "onReceive action: ", action);
                    FtUtil.log_i(AtFcfmtest.this.CLASS_NAME, "Stop Receiver ", "");
                    AtFcfmtest atFcfmtest2 = AtFcfmtest.this;
                    atFcfmtest2.stopReceiver(atFcfmtest2.mReceiver);
                    if (action.equals("test.mode.radio.on.response")) {
                        if ("OK".equals(intent.getStringExtra("success"))) {
                            AtFcfmtest atFcfmtest3 = AtFcfmtest.this;
                            atFcfmtest3.writer.write(atFcfmtest3.responseOK("0"));
                        } else {
                            AtFcfmtest atFcfmtest4 = AtFcfmtest.this;
                            atFcfmtest4.writer.write(atFcfmtest4.responseNG("0"));
                        }
                    } else if (action.equals("test.mode.radio.off.response")) {
                        AtFcfmtest atFcfmtest5 = AtFcfmtest.this;
                        atFcfmtest5.writer.write(atFcfmtest5.responseOK("0"));
                    } else if (action.equals("test.mode.radio.freq.response")) {
                        AtFcfmtest atFcfmtest6 = AtFcfmtest.this;
                        atFcfmtest6.writer.write(atFcfmtest6.responseString("1", intent.getStringExtra("signal_strength")));
                    }
                } catch (Throwable th) {
                    throw th;
                }
            }
        };
        atFcfmtest.CMD_NAME = "FCFMTEST";
        atFcfmtest.CLASS_NAME = "AtFcfmtest";
        atFcfmtest.NUM_ARGS = 4;
        atFcfmtest.writer = responseWriter;
        map60.put("AT+FCFMTEST", atFcfmtest);
        HashMap map61 = registerFactoryBinHandler.mAtHandlers;
        AtZigbtest atZigbtest = new AtZigbtest(registerFactoryBinHandler.mContext);
        atZigbtest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtZigbtest.1
            public AnonymousClass1() {
            }

            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context12, Intent intent) {
                String action = intent.getAction();
                LiveData$$ExternalSyntheticOutline0.m("action : ", action, AtZigbtest.this.CLASS_NAME, "onReceive");
                if ("com.sec.android.app.zigbeetest.ZIGBEE_TEST_RESPONSE".equals(action)) {
                    AtZigbtest atZigbtest2 = AtZigbtest.this;
                    atZigbtest2.context.unregisterReceiver(atZigbtest2.mReceiver);
                    String stringExtra = intent.getStringExtra("S_DATA");
                    if (stringExtra == null) {
                        stringExtra = intent.getStringExtra("I_DATA");
                    }
                    int intExtra = intent.getIntExtra("CMDID", 0);
                    DigitizerElectricService$1$$ExternalSyntheticOutline0.m(intExtra, "resCmd: ", AtZigbtest.this.CLASS_NAME, "onReceive");
                    AtZigbtest atZigbtest3 = AtZigbtest.this;
                    atZigbtest3.writer.write(atZigbtest3.responseString(Integer.toString(intExtra), stringExtra));
                }
            }
        };
        atZigbtest.CMD_NAME = "ZIGBTEST";
        atZigbtest.CLASS_NAME = "AtZigbtest";
        atZigbtest.NUM_ARGS = 4;
        atZigbtest.writer = responseWriter;
        map61.put("AT+ZIGBTEST", atZigbtest);
        if (ModuleCommon.instance(registerFactoryBinHandler.mContext).isConnectionModeNone() && Support$Path.getEnabled("AT_CALIDATE")) {
            HashMap map62 = registerFactoryBinHandler.mAtHandlers;
            AtCalidate atCalidate = new AtCalidate(registerFactoryBinHandler.mContext);
            atCalidate.CMD_NAME = "CALIDATE";
            atCalidate.CLASS_NAME = "AtCalidate";
            atCalidate.NUM_ARGS = 4;
            map62.put("AT+CALIDATE", atCalidate);
        }
        if ("true".equals(Support$Path.getEnableForAllMenu())) {
            Object atFpsensorGoodix = null;
            if (FactoryTest.isFactoryBinary()) {
                String fromPath = Support$Path.readFromPath("/sys/class/fingerprint/fingerprint/type_check", true);
                try {
                    i = Integer.parseInt(fromPath);
                } catch (NumberFormatException e) {
                    FtUtil.log_e(e);
                    i = -2;
                }
                if (i <= 0) {
                    LiveData$$ExternalSyntheticOutline0.m("[UTOPIA_FINGERPRINT] ", fromPath, "RegisterCommonHandler", "getFPSensorAtHandler");
                    FtUtil.log_d("RegisterCommonHandler", "getFPSensorAtHandler", "[UTOPIA_FINGERPRINT] fingerprint type_check is not normal(type <= 0). AT+FPSENSOR is not registered.");
                } else {
                    str = Support$Path.read("FINGERPRINT_VENDOR", true, true);
                    String str2 = Support$Path.read("FINGERPRINT_CHIP_NAME", true, true);
                    FtUtil.log_d("RegisterCommonHandler", "getFPSensorAtHandler", AtParser$$ExternalSyntheticOutline0.m(" Vendor:", str, " Name:", str2));
                    if (str != null || "".equalsIgnoreCase(str) || str2 == null || "".equalsIgnoreCase(str2)) {
                        registerCommonHandler$FPVendorChipValueOf = null;
                    } else {
                        registerCommonHandler$FPVendorChipValueOf = RegisterCommonHandler$FPVendorChip.INVALID_VAL;
                        try {
                            String upperCase = str.trim().toUpperCase(Locale.ENGLISH);
                            if ("EGISTEC".equals(upperCase) || "GOODIX".equals(upperCase) || "QCOM".equals(upperCase)) {
                                registerCommonHandler$FPVendorChipValueOf = RegisterCommonHandler$FPVendorChip.valueOf(upperCase);
                            }
                        } catch (NullPointerException e2) {
                            FtUtil.log_e(e2);
                        }
                    }
                    if (registerCommonHandler$FPVendorChipValueOf != null) {
                        iOrdinal = registerCommonHandler$FPVendorChipValueOf.ordinal();
                        responseWriter2 = registerFactoryBinHandler.mWriter;
                        if (iOrdinal != 0) {
                            atFpsensorGoodix = new AtFpsensorGoodix(registerFactoryBinHandler.mContext, responseWriter2);
                        } else if (iOrdinal != 1) {
                            atFpsensorGoodix = new AtFpsensorEgis(registerFactoryBinHandler.mContext, responseWriter2);
                        } else if (iOrdinal != 2) {
                            FtUtil.log_d("RegisterCommonHandler", "getFPSensorAtHandler", "Can not find the vendor's name or chip's name");
                        } else {
                            atFpsensorGoodix = new AtFpsensorQcom(registerFactoryBinHandler.mContext, responseWriter2);
                        }
                    }
                }
            } else {
                str = Support$Path.read("FINGERPRINT_VENDOR", true, true);
                String str3 = Support$Path.read("FINGERPRINT_CHIP_NAME", true, true);
                FtUtil.log_d("RegisterCommonHandler", "getFPSensorAtHandler", AtParser$$ExternalSyntheticOutline0.m(" Vendor:", str, " Name:", str3));
                if (str != null) {
                    registerCommonHandler$FPVendorChipValueOf = null;
                } else {
                    registerCommonHandler$FPVendorChipValueOf = null;
                }
                if (registerCommonHandler$FPVendorChipValueOf != null) {
                    iOrdinal = registerCommonHandler$FPVendorChipValueOf.ordinal();
                    responseWriter2 = registerFactoryBinHandler.mWriter;
                    if (iOrdinal != 0) {
                        atFpsensorGoodix = new AtFpsensorGoodix(registerFactoryBinHandler.mContext, responseWriter2);
                    } else if (iOrdinal != 1) {
                        atFpsensorGoodix = new AtFpsensorEgis(registerFactoryBinHandler.mContext, responseWriter2);
                    } else if (iOrdinal != 2) {
                        FtUtil.log_d("RegisterCommonHandler", "getFPSensorAtHandler", "Can not find the vendor's name or chip's name");
                    } else {
                        atFpsensorGoodix = new AtFpsensorQcom(registerFactoryBinHandler.mContext, responseWriter2);
                    }
                }
            }
            if (atFpsensorGoodix != null) {
                registerFactoryBinHandler.mAtHandlers.put("AT+FPSENSOR", atFpsensorGoodix);
            }
        }
        if (Support$Path.getEnabled("AT_GPSSTEST")) {
            HashMap map63 = registerFactoryBinHandler.mAtHandlers;
            AtGpsstest atGpsstest = new AtGpsstest(registerFactoryBinHandler.mContext);
            atGpsstest.argu0 = "0";
            atGpsstest.mReceiver = new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtGpsstest.1
                public AnonymousClass1() {
                }

                @Override // android.content.BroadcastReceiver
                public final void onReceive(Context context12, Intent intent) {
                    String action = intent.getAction();
                    if ("com.android.samsungtest.GPS_OK".equals(action)) {
                        AtGpsstest atGpsstest2 = AtGpsstest.this;
                        atGpsstest2.writer.write(atGpsstest2.responseString("0", "OK"));
                    }
                    if ("com.android.samsungtest.GPS_RESPONSE".equals(action)) {
                        String stringExtra = intent.getStringExtra("RES");
                        AtGpsstest atGpsstest3 = AtGpsstest.this;
                        atGpsstest3.writer.write(atGpsstest3.responseString(atGpsstest3.argu0, stringExtra));
                        FtUtil.log_i(AtGpsstest.this.CLASS_NAME, "responseString argu0" + AtGpsstest.this.argu0 + ", resData:" + stringExtra);
                    }
                    AtGpsstest atGpsstest4 = AtGpsstest.this;
                    atGpsstest4.stopReceiver(atGpsstest4.mReceiver);
                }
            };
            atGpsstest.CMD_NAME = "GPSSTEST";
            atGpsstest.CLASS_NAME = "AtGpsstest";
            atGpsstest.NUM_ARGS = 4;
            atGpsstest.writer = responseWriter;
            map63.put("AT+GPSSTEST", atGpsstest);
        }
        if (Support$Path.getBoolean("SUPPORT_AUDIO_HAL_AIDL")) {
            registerFactoryBinHandler.mAtHandlers.put("AT+SPKSTEST", new AtSpkstestNew(registerFactoryBinHandler.mContext));
        } else {
            registerFactoryBinHandler.mAtHandlers.put("AT+SPKSTEST", new AtSpkstest(registerFactoryBinHandler.mContext));
        }
        registerFactoryBinHandler.registerSpecificHandler();
        FtUtil.log_d("AtParser", "registerAllHandler", "registered AtHandlers");
        if (FactoryTest.isFactoryBinary()) {
            FtUtil.log_d("AtParser", "createCmdInfoFile", "");
            if (!Support$Path.isExistFilePath("data/log/ftl/cmdInfo") || (fileArrListFiles = new File("data/log/ftl/cmdInfo").listFiles()) == null) {
                this.mfileName = ProfileTranscoder$$ExternalSyntheticOutline0.m(new StringBuilder(), this.mfileName, "1");
            } else {
                this.mfileName += Integer.toString(fileArrListFiles.length);
            }
            FtUtil.log_d("AtParser", "createCmdInfoFile", "file name : " + this.mfileName);
            this.cmdInfoData = new File(ProfileTranscoder$$ExternalSyntheticOutline0.m(new StringBuilder("data/log/ftl/cmdInfo/"), this.mfileName, ".txt"));
        }
    }

    public final boolean runCmd(String str, ResponseWriter responseWriter) {
        String upperCase;
        String strHandleCommand;
        boolean z;
        FtUtil.log_d("AtParser", "runCmd", str);
        if (FactoryTest.isFactoryBinary()) {
            writeCmdInfoFile(str);
        }
        if (str != null) {
            try {
                if (str.length() >= 1) {
                    if (!str.contains("=") || str.indexOf("=") == 0) {
                        upperCase = str.contains("?") ? str.substring(0, str.indexOf("?")).toUpperCase(Locale.ENGLISH) : str.trim().substring(0, str.length()).toUpperCase(Locale.ENGLISH);
                    } else {
                        upperCase = str.substring(0, str.indexOf("=")).toUpperCase(Locale.ENGLISH);
                    }
                    FtUtil.log_d("AtParser", "process", "command : " + upperCase);
                    if (upperCase == null || !this.atHandlers.containsKey(upperCase) || isFilteredCommand(str, upperCase)) {
                        String upperCase2 = str.toUpperCase(Locale.ENGLISH);
                        Intent intent = new Intent("com.sec.factory.ACTION_15TEST_ALL_NV_CHECK");
                        intent.setPackage("com.sec.facuifunction");
                        if (upperCase2.contains("SETTESTNV") || upperCase2.contains("GETTESTNV")) {
                            this.mContext.sendBroadcast(intent, "com.sec.factory.permission.KEYSTRING");
                            try {
                                int i = Integer.parseInt(str.split("=")[1].split(",")[0]);
                                Intent intent2 = new Intent("com.sec.factory.CMD_NV_INFORMATION");
                                intent2.putExtra("nv", i);
                                this.mContext.sendBroadcast(intent2);
                            } catch (ArrayIndexOutOfBoundsException | NumberFormatException e) {
                                FtUtil.log_e(e);
                            }
                        } else if (upperCase2.contains("SETDOTESTNV") || upperCase2.contains("GETDOTESTNV")) {
                            this.mContext.sendBroadcast(intent, "com.sec.factory.permission.KEYSTRING");
                            try {
                                this.mContext.sendBroadcast(new Intent("com.sec.factory.CMD_NV_INFORMATION"));
                            } catch (NumberFormatException e2) {
                                FtUtil.log_e(e2);
                            }
                        }
                        Intent intent3 = new Intent("com.sec.factory.RECEIVED_FROM_RIL");
                        intent3.putExtra("command", str);
                        if ("AT+RSTVERIF=0,0".equalsIgnoreCase(str)) {
                            intent3.addFlags(268435456);
                        } else if ("AT+KSTRINGB=0,2".equalsIgnoreCase(str) || "AT+KSTRINGB=0,3".equalsIgnoreCase(str) || "AT+KSTRINGB=1,1".equalsIgnoreCase(str)) {
                            intent3.setPackage("com.sec.hiddenmenu");
                            intent3.addFlags(268435456);
                        } else if (str.contains("AT+SETTESTNV=117")) {
                            FtUtil.log_d("AtParser", "runCmd: ", str.concat(" (NFC_FT)"));
                        }
                        intent3.addFlags(16777216);
                        this.mContext.sendBroadcast(intent3);
                        FtUtil.log_d("AtParser", "runCmd: ", "Broadcast unregistered command: ".concat(str));
                        strHandleCommand = null;
                        z = true;
                    } else {
                        AtCommandHandler atCommandHandler = (AtCommandHandler) this.atHandlers.get(upperCase);
                        String[] strArrSplitArgu = splitArgu(str);
                        FtUtil.log_d("AtParser", "runCmd", FtUtil.setMspSeqMessage(0, str.replace("+", ":"), "Start"));
                        strHandleCommand = atCommandHandler.handleCommand(strArrSplitArgu);
                        FtUtil.log_d("AtParser", "runCmd: ", "CMD : " + str + ", result : " + strHandleCommand);
                        if (FactoryTest.isFactoryBinary()) {
                            writeCmdInfoFile(strHandleCommand);
                        }
                        AtCommandInfo.getInstance().addCommandHistory("Registered CMD : ".concat(str));
                        z = false;
                    }
                    if (strHandleCommand == null) {
                        return z;
                    }
                    if ("NOT_APPLICABLE".equals(strHandleCommand)) {
                        return true;
                    }
                    responseWriter.write(strHandleCommand);
                    return true;
                }
            } catch (StringIndexOutOfBoundsException e3) {
                FtUtil.log_e(e3);
            }
        }
        return false;
    }

    public final void writeCmdInfoFile(String str) {
        LiveData$$ExternalSyntheticOutline0.m("data= ", str, "AtParser", "writeCmdInfoFile");
        try {
            BufferedWriter bufferedWriter = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(this.cmdInfoData), Charset.defaultCharset()));
            try {
                String str2 = new SimpleDateFormat("HH:mm:ss").format(Long.valueOf(System.currentTimeMillis()));
                BufferedWriter bufferedWriter2 = new BufferedWriter(bufferedWriter);
                bufferedWriter2.append((CharSequence) ("[" + str2 + "]\t\t"));
                bufferedWriter2.append((CharSequence) (str + "\n\n"));
                bufferedWriter2.close();
                bufferedWriter.close();
            } catch (Throwable th) {
                try {
                    bufferedWriter.close();
                } catch (Throwable th2) {
                    th.addSuppressed(th2);
                }
                throw th;
            }
        } catch (IOException unused) {
        }
    }
}
