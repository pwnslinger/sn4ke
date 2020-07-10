#include <stdio.h>

int main() {
    int i;
    scanf("%d", &i);
    if (i == 0x1337) {
        printf("Winner!");
    } else {
        printf("Nope!");
    }
    return 0;
}

