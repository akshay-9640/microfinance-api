package com.microfinance.api.controller;


import com.microfinance.api.dao.ImWalletTransactionsDao;
import com.microfinance.api.model.ImWalletTransactions;
import com.microfinance.api.model.WithdrawlByAgentrequest;
import com.microfinance.api.model.versionrequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/fin")
public class WithdrawalReportController {
    private final ImWalletTransactionsDao imWalletTransactionsDao;

    public WithdrawalReportController(ImWalletTransactionsDao imWalletTransactionsDao) {
        this.imWalletTransactionsDao = imWalletTransactionsDao;
    }
    @GetMapping("/getallwithdrawal")
    public List<ImWalletTransactions> get(){
        return imWalletTransactionsDao.getAllwithdraw();
    }

    @PostMapping(path = "/getbwdates")
    public List<ImWalletTransactions> getAllBetweendatesLoans(@RequestBody versionrequest vr) {
        List<ImWalletTransactions> x = imWalletTransactionsDao.getAllBetweendatesLoans(vr.getDate1(), vr.getDate2());
        return x;
    }

    @PostMapping(path = "/getbwdatesbyagent")
    public List<ImWalletTransactions> getAllBetweendateswithbyagentid(@RequestBody WithdrawlByAgentrequest td) {
        List<ImWalletTransactions> x = imWalletTransactionsDao.getAllBetweendatesByAgid(td.getAgentid(),td.getDate1(), td.getDate2());
        return x;
    }
    @GetMapping("/getaepswithdrawal")
    public int opencount() {
        int x = imWalletTransactionsDao.getaepswithdraw();
        return x;
    }

    @GetMapping("/getaepsmini")
    public int MiniStatement() {
        int x = imWalletTransactionsDao.getaepsminist();
        return x;
    }

    @GetMapping("/getaepsbal")
    public int Balanceen() {
        int x = imWalletTransactionsDao.getaepsbalcenq();
        return x;
    }
}
