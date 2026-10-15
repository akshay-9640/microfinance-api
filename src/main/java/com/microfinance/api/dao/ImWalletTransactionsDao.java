package com.microfinance.api.dao;

import com.microfinance.api.model.ImWalletTransactions;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
@Repository
public interface ImWalletTransactionsDao extends JpaRepository<ImWalletTransactions, Long> {

    @Query(value = "SELECT distinct awt.txntypeid,awt.id as id, awt.agentid as agentid,awt.refid AS refid ,awt.txnamount AS txnamount,ROUND((aw.txnamount*100)/95) as commsion,date(aw.txndatetime) AS txndatetime FROM imagentwallettransactions awt, imagentwallettransactions aw WHERE awt.txntypeid IN ('2','3') AND awt.agentid=aw.agentid AND awt.id=aw.refid", nativeQuery=true)
    List<ImWalletTransactions> getAllwithdraw();

    @Query(value = "SELECT distinct awt.txntypeid,awt.id as id, awt.agentid as agentid,awt.refid AS refid ,awt.txnamount AS txnamount,ROUND((aw.txnamount*100)/95) as commsion,date(aw.txndatetime) AS txndatetime FROM imagentwallettransactions awt, imagentwallettransactions aw WHERE awt.txntypeid IN ('2','3') AND awt.agentid=aw.agentid AND awt.id=aw.refid AND date(aw.txndatetime) BETWEEN  ?1 and ?2", nativeQuery=true)
    List<ImWalletTransactions> getAllBetweendatesLoans(String date1, String date2);

    @Query(value = "SELECT distinct awt.txntypeid,awt.id as id, awt.agentid as agentid,awt.refid AS refid ,awt.txnamount AS txnamount,ROUND((aw.txnamount*100)/95) as commsion,date(aw.txndatetime) AS txndatetime FROM imagentwallettransactions awt, imagentwallettransactions aw WHERE awt.txntypeid IN ('2','3') AND awt.agentid=?1 AND awt.agentid=aw.agentid AND awt.id=aw.refid AND date(aw.txndatetime) BETWEEN  ?2 and ?3", nativeQuery=true)
    List<ImWalletTransactions> getAllBetweendatesByAgid(String agentid,String date1, String date2);

    @Query(value = "SELECT count(id) AS Withdrawamount FROM instant_pay_withdrawal_response_data", nativeQuery=true)
    int getaepswithdraw();

    @Query(value = "SELECT count(id) AS MiniStatement FROM instant_pay_mini_statement_response_ministatement ;", nativeQuery=true)
    int getaepsminist();

    @Query(value = "SELECT count(id) AS MiniStatement FROM instant_pay_balance_enquiry_response_data ;", nativeQuery=true)
    int getaepsbalcenq();


}
