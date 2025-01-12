function addToCart(roomId) {
        fetch(`/add_to_cart/${roomId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Cập nhật số lượng hiển thị trong giỏ hàng ngay lập tức
                document.getElementById('cart-count').textContent = data.cart_size;
            }
        })
        .catch(error => console.error('Error:', error));
    }

function removeFromCart(roomId) {
    fetch(`/remove_from_cart/${roomId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            console.error('Network response was not ok', response);
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const cartCounter = document.getElementById('cart-count');
            if (cartCounter) {
                cartCounter.textContent = data.cart_size;
            } else {
                console.warn("Không tìm thấy phần tử với id 'cart-count'");
            }
            const itemElement = document.getElementById(`cart-item-${roomId}`);
            if (itemElement) {
                itemElement.remove();
            }

            const totalElement = document.getElementById('total-price');
            if (totalElement) {
                totalElement.textContent = `${data.total.toLocaleString()} VND`;
            }
        } else {
            console.error("Không thể xóa phòng khỏi giỏ hàng", data);
        }
    })
    .catch(error => console.error('Error:', error));
}

function addComment(roomId) {
    if (confirm("Bạn chắc chắn thêm bình luận?") === true) {
        fetch(`/api/products/${productId}/comments`, {
             method: "post",
            body: JSON.stringify({
                "content": document.getElementById('comment').value
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(res => res.json()).then(data => {
            if (data.status === 200) {
                let c = data.comment;
                let d = document.getElementById("comments");
                d.innerHTML = `
                    <div class="row alert alert-info">
                        <div class="col-md-1 col-xs-4">
                            <img src="${c.user.avatar}" class="img-fluid rounded" />
                        </div>
                        <div class="col-md-11 col-xs-8">
                            <p><strong>${c.comments}</strong></p>
                            <p>Bình luận lúc: <span class="date">${ moment(c.create_at).locale("vi").fromNow() }</span></p>
                        </div>
                    </div>
                ` + d.innerHTML;
            } else
                alert(data.err_msg);
        })
    }
}