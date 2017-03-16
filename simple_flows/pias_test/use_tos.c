#include <assert.h>
#include <netinet/ip.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <stdint.h>

void test_setsockopt()
{
  int priority = 6;
  int iptos = IPTOS_CLASS_CS6;

  int fd = socket(AF_INET, SOCK_STREAM, 0);

  if(setsockopt(fd, SOL_SOCKET, SO_PRIORITY, &priority,
                sizeof(priority)) < 0){
    printf("Oh no\n");
  }

  /*int tos = -1;
  socklen_t optlen = sizeof(tos);
  if (getsockopt(fd, IPPROTO_IP, IP_TOS, &tos, &optlen) < 0){
    printf("Oh no\n");
  }*/

  
  uint8_t new_tos = 0x08; 

  if(setsockopt(fd, IPPROTO_IP, IP_TOS, &new_tos, sizeof(new_tos)) < 0)
  {
    printf("Cannot set TOS of IP\n");
  }

  int rt_tos = -1;
  socklen_t optlen = sizeof(rt_tos);

  if (getsockopt(fd, IPPROTO_IP, IP_TOS, &rt_tos, &optlen) < 0){
    printf("Oh no IP\n");
  }
  
   const int print_int = (rt_tos & 0xff);
   printf("Retrieved TOS: %d\n", print_int);

  close(fd);
}

int main(void)
{
  // background: https://ocrete.ca/2009/07/24/when-a-man-page-lies/
  test_setsockopt();

  return 0;
}
