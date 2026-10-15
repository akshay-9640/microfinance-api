package com.microfinance.api.dao;

import com.microfinance.api.model.FinLoginLogs;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface FinLoginLogsDao extends JpaRepository <FinLoginLogs, Integer>{

}
