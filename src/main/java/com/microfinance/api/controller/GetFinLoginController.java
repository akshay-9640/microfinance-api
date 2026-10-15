package com.microfinance.api.controller;


import com.microfinance.api.dao.FinLoginLogsDao;
import com.microfinance.api.dao.GetFinLoginDao;
import com.microfinance.api.model.ChangePasswordRequest;
import com.microfinance.api.model.FinLoginLogs;
import com.microfinance.api.model.GetFinLogin;
import com.microfinance.api.model.UserRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@RequestMapping("/fin/auth")
public class GetFinLoginController {

    private static final Logger log = LoggerFactory.getLogger(GetFinLoginController.class);

    private final PasswordEncoder passwordEncoder;
    private final GetFinLoginDao getFinLoginDao;
    private final FinLoginLogsDao finLoginLogsDao;

    public GetFinLoginController(PasswordEncoder passwordEncoder, GetFinLoginDao getFinLoginDao,
                                 FinLoginLogsDao finLoginLogsDao) {
        this.passwordEncoder = passwordEncoder;
        this.getFinLoginDao = getFinLoginDao;
        this.finLoginLogsDao = finLoginLogsDao;
    }

    // Unknown user and wrong password return the same response, so the endpoint
    // cannot be used to find out which usernames exist. Passwords are never logged.
    @PostMapping(path = "/login")
    public ResponseObject<String> login(@Valid @RequestBody UserRequest vr) {
        GetFinLogin user = getFinLoginDao.getHeadofficeLogin(vr.getUsername());
        if (user == null || !passwordEncoder.matches(vr.getPassword(), user.getPassword())) {
            log.info("Failed login attempt for username '{}'", vr.getUsername());
            return new ResponseObject<>(401, "ERROR");
        }
        return new ResponseObject<>(200, "OK");
    }

    // Requires the user's own password, and the password hash is never serialized
    // (see GetFinLogin.password).
    @PostMapping("/getuserdata")
    public Object getHeadofficeLogin(@Valid @RequestBody UserRequest vr) {
        GetFinLogin user = getFinLoginDao.getHeadofficeLogin(vr.getUsername());
        if (user == null || !passwordEncoder.matches(vr.getPassword(), user.getPassword())) {
            return new ResponseObject<>(401, "ERROR");
        }
        return user;
    }

    // Changing a password requires the current password. This used to be an
    // unauthenticated GET that reset any user's password from a username alone.
    @PostMapping(path = "/updatePassword")
    public ResponseObject<String> updatePassword(@Valid @RequestBody ChangePasswordRequest req) {
        GetFinLogin user = getFinLoginDao.getHeadofficeLogin(req.getUsername());
        if (user == null || !passwordEncoder.matches(req.getCurrentPassword(), user.getPassword())) {
            log.info("Rejected password change for username '{}'", req.getUsername());
            return new ResponseObject<>(401, "ERROR");
        }
        user.setPassword(passwordEncoder.encode(req.getNewPassword()));
        getFinLoginDao.save(user);
        return new ResponseObject<>(200, "OK");
    }

    @PostMapping("/loginlog")
    public FinLoginLogs insertLoginLog(@RequestBody FinLoginLogs finLoginLogs) {
        return finLoginLogsDao.save(finLoginLogs);
    }
}
