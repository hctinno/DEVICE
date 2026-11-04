package com.samsung.android.nfc.nci;

import src.com.samsung.android.nfc.nci.NciUtil;

/* JADX INFO: loaded from: classes.dex */
public abstract class SamsungNciPacket extends NciPacket {
    protected byte mSubGid;
    protected byte mSubOid;

    public static byte byteToSubGid(byte b) {
        return (byte) ((b >> 4) & 15);
    }

    public static byte byteToSubOid(byte b) {
        return (byte) (b & 15);
    }

    protected SamsungNciPacket(byte b, byte b2, byte b3, byte[] bArr) {
        super(b, b2, b3, bArr);
        this.mSubGid = byteToSubGid(bArr[0]);
        this.mSubOid = byteToSubOid(bArr[0]);
    }

    protected SamsungNciPacket(byte b, byte[] bArr) {
        this(b, (byte) 15, (byte) 62, bArr);
    }

    @Override // com.samsung.android.nfc.nci.NciPacket
    public String toString() {
        StringBuilder sb = new StringBuilder("Samsung NCI[");
        sb.append("(G)" + NciUtil.subGidToString(this.mSubGid));
        sb.append(":(O)" + NciUtil.subOidToString(this.mSubGid, this.mSubOid));
        sb.append(":(P):0x" + NciUtil.bytesToString(this.mPayload) + "]");
        return sb.toString();
    }
}
