package com.microfinance.api.model;


import javax.persistence.*;

@Entity
@Table(name = "imagentwallettransactions")
public class ImWalletTransactions {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column
    private Long id;
    @Column
    private String agentid;
    @Column
    private String refid;
    @Column
    private String txnamount;
    @Column
    private String txndatetime;
    @Column
    private String txntypeid;
    String commsion;

    public String getCommsion() {
        return commsion;
    }

    public void setCommsion(String commsion) {
        this.commsion = commsion;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getAgentid() {
        return agentid;
    }

    public void setAgentid(String agentid) {
        this.agentid = agentid;
    }

    public String getRefid() {
        return refid;
    }

    public void setRefid(String refid) {
        this.refid = refid;
    }

    public String getTxnamount() {
        return txnamount;
    }

    public void setTxnamount(String txnamount) {
        this.txnamount = txnamount;
    }

    public String getTxndatetime() {
        return txndatetime;
    }

    public void setTxndatetime(String txndatetime) {
        this.txndatetime = txndatetime;
    }

    public String getTxntypeid() {
        return txntypeid;
    }

    public void setTxntypeid(String txntypeid) {
        this.txntypeid = txntypeid;
    }
}
