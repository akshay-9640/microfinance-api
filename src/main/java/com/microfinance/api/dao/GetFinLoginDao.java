package com.microfinance.api.dao;

import com.microfinance.api.model.GetFinLogin;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface GetFinLoginDao extends JpaRepository<GetFinLogin, Long> {
    @Query(value = "Select bl from GetFinLogin bl where bl.username=?1")
    GetFinLogin getHeadofficeLogin(String username);

}
