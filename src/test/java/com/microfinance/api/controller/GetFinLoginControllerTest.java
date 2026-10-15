package com.microfinance.api.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microfinance.api.dao.FinLoginLogsDao;
import com.microfinance.api.dao.GetFinLoginDao;
import com.microfinance.api.model.ChangePasswordRequest;
import com.microfinance.api.model.GetFinLogin;
import com.microfinance.api.model.UserRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

// Plain unit tests: no database, no Spring context.
class GetFinLoginControllerTest {

    private final PasswordEncoder encoder = new BCryptPasswordEncoder();
    private GetFinLoginDao users;
    private GetFinLoginController controller;
    private GetFinLogin alice;

    @BeforeEach
    void setUp() {
        users = mock(GetFinLoginDao.class);
        controller = new GetFinLoginController(encoder, users, mock(FinLoginLogsDao.class));
        alice = new GetFinLogin();
        alice.setUsername("alice");
        alice.setPassword(encoder.encode("correct-horse"));
        alice.setMobile("0000000000");
        when(users.getHeadofficeLogin("alice")).thenReturn(alice);
    }

    @Test
    void loginSucceedsOnlyWithTheRightPassword() {
        assertEquals(200, controller.login(new UserRequest("alice", "correct-horse")).getStatus());
        assertEquals(401, controller.login(new UserRequest("alice", "wrong")).getStatus());
    }

    @Test
    void unknownUserLooksExactlyLikeWrongPassword() {
        ResponseObject<String> unknown = controller.login(new UserRequest("nobody", "x"));
        ResponseObject<String> wrong = controller.login(new UserRequest("alice", "x"));
        assertEquals(wrong.getStatus(), unknown.getStatus());
        assertEquals(wrong.getMessage(), unknown.getMessage());
    }

    @Test
    void passwordChangeRequiresTheCurrentPassword() {
        ChangePasswordRequest req = new ChangePasswordRequest();
        req.setUsername("alice");
        req.setCurrentPassword("guess");
        req.setNewPassword("attacker-chosen");
        assertEquals(401, controller.updatePassword(req).getStatus());
        verify(users, never()).save(any());

        req.setCurrentPassword("correct-horse");
        assertEquals(200, controller.updatePassword(req).getStatus());
        verify(users).save(alice);
        assertTrue(encoder.matches("attacker-chosen", alice.getPassword()));
    }

    @Test
    void userDataNeedsThePasswordAndNeverIncludesTheHash() throws Exception {
        assertTrue(controller.getHeadofficeLogin(new UserRequest("alice", "wrong")) instanceof ResponseObject);

        Object body = controller.getHeadofficeLogin(new UserRequest("alice", "correct-horse"));
        String json = new ObjectMapper().writeValueAsString(body);
        assertTrue(json.contains("\"username\":\"alice\""));
        assertFalse(json.contains("password"), json);
        assertFalse(json.contains(alice.getPassword()), json);
    }
}
