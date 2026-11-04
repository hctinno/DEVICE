package com.sec.facatfunction.aporiented.athandler;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import com.sec.factorymodule.modules.ModuleCommunication;
import com.sec.xmldata.support.XmlUtil;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtBtletest extends AtCommandHandler {
    public String first_argu;

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public final synchronized String handleCommand(String[] strArr) {
        String str;
        try {
            if (strArr.length != this.NUM_ARGS) {
                AtCommandHandler.responseNA();
                return "\r\n+CME Error:NA\r\n\r\nOK\r\n";
            }
            try {
                this.first_argu = strArr[0];
                int i = Integer.parseInt(strArr[3]);
                if (checkArgu(strArr, new String[]{"0", "0", "0"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance.CLASS_NAME, "setBtLeTxOutputCh", "setBtLeTxOutputCh ch : " + i);
                    moduleCommunicationInstance.requestActionToBTService(60, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "1"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance2 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance2.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance2.CLASS_NAME, "setBtLeTxMod0FCh", "setBtLeTxMod0FCh ch : " + i);
                    moduleCommunicationInstance2.requestActionToBTService(61, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "2"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance3 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance3.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance3.CLASS_NAME, "setBtLeTxModAACh", "setBtLeTxModAACh ch : " + i);
                    moduleCommunicationInstance3.requestActionToBTService(62, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "3"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance4 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance4.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance4.CLASS_NAME, "setBtLeTxCarrierCh", "setBtLeTxCarrierCh ch : " + i);
                    moduleCommunicationInstance4.requestActionToBTService(63, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "4"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance5 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance5.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance5.CLASS_NAME, "setBtLeTxInbandCh", "setBtLeTxInbandCh ch : " + i);
                    moduleCommunicationInstance5.requestActionToBTService(64, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "5"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance6 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance6.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance6.CLASS_NAME, "setBtLeRxCh", "setBtLeRxCh ch : " + i);
                    moduleCommunicationInstance6.requestActionToBTService(65, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "6"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance7 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance7.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance7.CLASS_NAME, "setBtLeRxPhyCh", "setBtLeRxPhyCh ch : " + i);
                    moduleCommunicationInstance7.requestActionToBTService(66, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "7"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance8 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance8.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance8.CLASS_NAME, "setBtLeRxModeIndexCh", "setBtLeRxModeIndexCh ch : " + i);
                    moduleCommunicationInstance8.requestActionToBTService(67, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "8"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance9 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance9.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance9.CLASS_NAME, "setBtLeTxModPhyCh", "setBtLeTxModPhyCh ch : " + i);
                    moduleCommunicationInstance9.requestActionToBTService(68, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "9"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance10 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance10.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance10.CLASS_NAME, "setBtLeTxModCh", "setBtLeTxModCh ch : " + i);
                    moduleCommunicationInstance10.requestActionToBTService(69, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "10"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance11 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance11.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance11.CLASS_NAME, "startBtLeChannel", "startBtLeChannel ch : " + i);
                    moduleCommunicationInstance11.requestActionToBTService(83, i);
                } else if (checkArgu(strArr, new String[]{"0", "0", "11", "0"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance12 = ModuleCommunication.instance(this.context);
                    XmlUtil.log_i(moduleCommunicationInstance12.CLASS_NAME, "stopBtLeChannel");
                    moduleCommunicationInstance12.requestActionToBTService(84);
                } else if (checkArgu(strArr, new String[]{"0", "0", "12", "0"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance13 = ModuleCommunication.instance(this.context);
                    XmlUtil.log_i(moduleCommunicationInstance13.CLASS_NAME, "stopBtLeChannel");
                    moduleCommunicationInstance13.requestActionToBTService(85);
                } else if (checkArgu(strArr, new String[]{"0", "0", "13"})) {
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance14 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance14.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance14.CLASS_NAME, "setBtLeTxPower", "setBtLeTxPower power : " + i);
                    moduleCommunicationInstance14.requestActionToBTService(86, i);
                } else {
                    if (!checkArgu(strArr, new String[]{"0", "0", "14"})) {
                        if (checkArgu(strArr, new String[]{"1", "0", "0"})) {
                            startReceiver();
                            ModuleCommunication moduleCommunicationInstance15 = ModuleCommunication.instance(this.context);
                            moduleCommunicationInstance15.getClass();
                            XmlUtil.log_i(moduleCommunicationInstance15.CLASS_NAME, "btLeRxTestResult", "btLeRxTestResult arg: " + i);
                            moduleCommunicationInstance15.requestActionToBTService(82, i);
                        } else {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                        return str;
                    }
                    startReceiver();
                    ModuleCommunication moduleCommunicationInstance16 = ModuleCommunication.instance(this.context);
                    moduleCommunicationInstance16.getClass();
                    XmlUtil.log_i(moduleCommunicationInstance16.CLASS_NAME, "setBtLeTxLength", "setBtLeTxLength length : " + i);
                    moduleCommunicationInstance16.requestActionToBTService(87, i);
                }
                str = null;
                return str;
            } catch (NumberFormatException e) {
                e.printStackTrace();
                return responseNG(strArr[0]);
            }
        } catch (Throwable th) {
            throw th;
        }
    }

    public final void startReceiver() {
        this.context.registerReceiver(new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtBtletest.1
            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context, Intent intent) {
                if ("com.sec.factory.intent.ACTION_BT_SERVICE_RESPONSE".equals(intent.getAction())) {
                    String stringExtra = intent.getStringExtra("result");
                    AtApchiptt$$ExternalSyntheticOutline0.m("EXTRA_KEY_BT_SERVICE_RESPONSE result=", stringExtra, AtBtletest.this.CLASS_NAME, "btReceiver.onReceive");
                    AtBtletest atBtletest = AtBtletest.this;
                    atBtletest.writer.write(atBtletest.responseString(atBtletest.first_argu, stringExtra));
                    AtBtletest.this.stopReceiver(this);
                }
            }
        }, new IntentFilter("com.sec.factory.intent.ACTION_BT_SERVICE_RESPONSE"), 2);
    }
}
