package com.microfinance.api.model;

import javax.persistence.*;

@Entity
@Table(name = "webloginlogs")
public class FinLoginLogs {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column
    private Long id;
    @Column
    private String module;
    @Column
    private String username;
    @Column
    private String status;
    @Column
    private String ip;
    @Column
    private String postingdate;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getModule() {
        return module;
    }

    public void setModule(String module) {
        this.module = module;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getIp() {
        return ip;
    }

    public void setIp(String ip) {
        this.ip = ip;
    }

    public String getPostingdate() {
        return postingdate;
    }

    public void setPostingdate(String postingdate) {
        this.postingdate = postingdate;
    }

    public FinLoginLogs(Long id, String module, String username, String status, String ip, String postingdate) {
        this.id = id;
        this.module = module;
        this.username = username;
        this.status = status;
        this.ip = ip;
        this.postingdate = postingdate;
    }

    public FinLoginLogs(){

    }
}
