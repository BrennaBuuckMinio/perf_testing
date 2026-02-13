select  *
from (select avg(ss_list_price) B1_LP
            ,count(ss_list_price) B1_CNT
            ,count(distinct ss_list_price) B1_CNTD
      from store_sales
      where ss_quantity between 0 and 5
        and (ss_list_price between 28.00 and 38.00 
             or ss_coupon_amt between 12573.00 and 13573.00
             or ss_wholesale_cost between 33.00 and 53.00)) B1,
     (select avg(ss_list_price) B2_LP
            ,count(ss_list_price) B2_CNT
            ,count(distinct ss_list_price) B2_CNTD
      from store_sales
      where ss_quantity between 6 and 10
        and (ss_list_price between 143.00 and 153.00
          or ss_coupon_amt between 5562.00 and 6562.00
          or ss_wholesale_cost between 45.00 and 65.00)) B2,
     (select avg(ss_list_price) B3_LP
            ,count(ss_list_price) B3_CNT
            ,count(distinct ss_list_price) B3_CNTD
      from store_sales
      where ss_quantity between 11 and 15
        and (ss_list_price between 159.00 and 169.00
          or ss_coupon_amt between 2807.00 and 3807.00
          or ss_wholesale_cost between 24.00 and 44.00)) B3,
     (select avg(ss_list_price) B4_LP
            ,count(ss_list_price) B4_CNT
            ,count(distinct ss_list_price) B4_CNTD
      from store_sales
      where ss_quantity between 16 and 20
        and (ss_list_price between 24.00 and 34.00
          or ss_coupon_amt between 3706.00 and 4706.00
          or ss_wholesale_cost between 46.00 and 66.00)) B4,
     (select avg(ss_list_price) B5_LP
            ,count(ss_list_price) B5_CNT
            ,count(distinct ss_list_price) B5_CNTD
      from store_sales
      where ss_quantity between 21 and 25
        and (ss_list_price between 76.00 and 86.00
          or ss_coupon_amt between 2096.00 and 3096.00
          or ss_wholesale_cost between 50.00 and 70.00)) B5,
     (select avg(ss_list_price) B6_LP
            ,count(ss_list_price) B6_CNT
            ,count(distinct ss_list_price) B6_CNTD
      from store_sales
      where ss_quantity between 26 and 30
        and (ss_list_price between 169.00 and 179.00
          or ss_coupon_amt between 10672.00 and 11672.00
          or ss_wholesale_cost between 58.00 and 78.00)) B6
limit 100;
